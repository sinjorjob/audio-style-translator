import os
from pydub import AudioSegment
import math
from openai import OpenAI
import tempfile
import re
import unicodedata
import configparser
import argparse
import json

class TranslationStyle:
    PODCAST = "podcast"
    SUNDAY_JAPON = "sunday_japon"
    NEWS_REPORT = "news_report"

    @staticmethod
    def get_prompt(style):
        print(f"Input style: {style}")  # デバッグ用

        prompts = {
            "podcast": """あなたは、英語のコンテンツを魅力的な日本語のポッドキャスト形式に変換する専門家です。
以下の要素を組み込んで、自然で魅力的な対話を作成してください：

1. 会話の構造とフロー
- ホストとゲストの自然な対話を作成
- 話題の導入、展開、まとめの流れを意識
- 適切な相づち（「なるほど」「そうですね」）や間投詞（「えーと」「あの」）を活用
- 会話の途中で相手の発言に関連づけた質問や意見を挟む

2. 話し言葉としての特徴
- カジュアルでありながら品位のある会話表現を使用
- 文脈に応じて適切な敬語レベルを選択
- 声に出した時の自然なリズム感を重視""",

            "sunday_japon": """あなたは、英語のコンテンツを爆笑問題の司会するサンデージャポンさながらの
討論バラエティ番組形式に変換するスペシャリストです。
以下の要素をふんだんに盛り込み、太田光風の毒舌＆鋭い分析と、田中裕二風の庶民目線のツッコミが
絶妙に交差する、テンポの良い笑いと議論を作り上げてください！

1. 討論・トークの特徴
- 太田光ばりの毒舌や時事問題へのズバッとした切り込み
- 田中裕二による“えー、それは変でしょう！”などのわかりやすいツッコミ
- パネリスト（出演者）も登場し、予想外のボケや論点ずらしに対して鋭く切り返し
- ワイドショー的に扱う時事ネタやポップカルチャーを遠慮なく投入
- 急に視点を切り替えて「まじめに考えましょうよ！」など、笑いから真面目モードへの素早い転換

2. 話し方・掛け合いの特徴
- ツッコミフレーズや「ちょっと待ってよ！」「それヤバくない！？」「いや、意味わかんない！」など、
  バラエティ特有の勢いのある言い回しを多用
- 田中風の「いやいや、そんなわけないでしょ？」といった“庶民目線”での相槌や苦笑い
- 太田風のシニカル・皮肉混じりのコメントで笑いを誘う
- 適度なオーバーリアクション、大げさな表現で場を盛り上げる
- 「スポンサー大丈夫かな？」などの番組風自虐ネタもOK

3. 演出・番組の雰囲気
- 爆笑問題特有の掛け合いが番組の主軸。太田がボケや挑発的なコメント、田中が落ち着いたトーンでのツッコミ
- 「みなさん、どうですか？」とパネリストに話を振り、時にショッキングな意見や茶々を入れて爆笑を誘う
- 大げさな驚き効果音を想起させるような言葉（「ええーっ！？」「ウソでしょ！」など）を要所で挿入
- 真面目な話題やデータを取り上げつつも、笑いを絶やさないバラエティ感
- “芸能ネタ”や“ネットでバズっている話題”を時々挟みつつ、時事・政治ネタもしっかり論じる
""",
            "news_report": """あなたは、英語のコンテンツを信頼性の高いニュースリポート形式に変換する専門家です。
以下の要素を組み込んで、正確で分かりやすい報道を作成してください：

1. 報道の特徴
- 客観的で正確な事実伝達
- 簡潔明瞭な表現
- 信頼感のあるトーン
- 重要なポイントの強調

2. 話し方の特徴
- フォーマルで丁寧な言葉遣い
- 明瞭な発音と適切な間の取り方
- 中立的な立場からの解説
- 専門用語の分かりやすい説明"""
        }

        common_requirements = """

必須条件：
- 各発言の前に[話者A]または[話者B]のみを明示的に付与
- 同じ話者には一貫して同じラベルを使用
- [話者A]をメイン話者、[話者B]をサブ話者として設定(この２名以外の話者の利用は禁止)
- 音声変換時の品質を考慮し、読点の位置や文の長さに注意

上記のすべてを踏まえつつ、以下の英語テキストを仕立て直してください。
"""
        if style not in prompts:
            print(f"Warning: Invalid style '{style}' specified, using default podcast style")
            style = "podcast"

        selected_prompt = prompts[style]
        print(f"Selected prompt: {selected_prompt[:100]}...")  # デバッグ用
        return selected_prompt + common_requirements

class AudioTranslator:
    def __init__(self, config_path='config.ini'):
        # Load configuration
        config = configparser.ConfigParser()
        config.read(config_path)
        
        # Get OpenAI settings
        self.openai_api_key = config['OpenAI']['api_key']
        self.transcription_model = config['Models']['transcription_model']
        self.translation_model = config['Models']['translation_model']
        self.tts_model = config['Models']['tts_model']
        self.html_generation_model = config['Models']['html_generation_model']
        
        # Get translation style
        self.translation_style = config.get('Translation', 'style', 
                                          fallback="podcast")
        print(f"Loaded style from config: {self.translation_style}")  # デバッグ追加

        self.client = OpenAI(api_key=self.openai_api_key)
        self.MAX_FILE_SIZE = 24 * 1024 * 1024

    # 以下のメソッドは変更なし
    def split_audio(self, audio_path):
        """Split audio file into chunks smaller than 25MB"""
        audio = AudioSegment.from_wav(audio_path)
        duration_ms = len(audio)
        
        file_size = os.path.getsize(audio_path)
        chunk_count = math.ceil(file_size / self.MAX_FILE_SIZE)
        chunk_duration = duration_ms // chunk_count

        chunks = []
        for i in range(chunk_count):
            start_time = i * chunk_duration
            end_time = (i + 1) * chunk_duration if i < chunk_count - 1 else duration_ms
            
            chunk = audio[start_time:end_time]
            chunk_path = f"temp_chunk_{i}.wav"
            chunk.export(chunk_path, format="wav")
            chunks.append(chunk_path)
        
        return chunks

    def transcribe_audio(self, audio_path):
        """Convert audio to English text using OpenAI Whisper API"""
        if os.path.getsize(audio_path) > self.MAX_FILE_SIZE:
            print("File too large, splitting into chunks...")
            chunks = self.split_audio(audio_path)
            transcripts = []
            
            for chunk_path in chunks:
                with open(chunk_path, "rb") as audio_file:
                    transcript = self.client.audio.transcriptions.create(
                        model=self.transcription_model,
                        file=audio_file
                    )
                transcripts.append(transcript.text)
                os.remove(chunk_path)  # Clean up chunk file
            
            return " ".join(transcripts)
        else:
            with open(audio_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model=self.transcription_model,
                    file=audio_file
                )
            return transcript.text

    def normalize_japanese_text(self, text):
        """テキスト正規化：全角半角の統一、不要な空白の削除、記号の整形など"""
        normalized = unicodedata.normalize("NFKC", text)
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = normalized.strip()
        return normalized

    def translate_to_japanese(self, english_text):
        """Translate English text to Japanese using GPT-4 with specified style"""
        translation_prompt = TranslationStyle.get_prompt(self.translation_style)
        print(f"Using style: {self.translation_style}")  # デバッグ追加

        response = self.client.chat.completions.create(
            model=self.translation_model,
            messages=[
                {"role": "user", "content": translation_prompt + english_text}
            ]
        )
        japanese_text = response.choices[0].message.content
        return self.normalize_japanese_text(japanese_text)

    def split_by_speaker(self, japanese_text):
        """Split text into segments by speaker"""
        segments = []
        pattern = r'(\[話者[AB]\])([^\\[]+?)(?=(\[話者[AB]\]|$))'
        matches = re.findall(pattern, japanese_text, re.DOTALL)
        
        for match in matches:
            speaker_label = match[0]
            text = match[1].strip()
            speaker = re.sub(r'\W', '', speaker_label)
            segments.append({
                'speaker': speaker[-1],
                'text': text
            })
        return segments

    def generate_japanese_audio(self, japanese_text, output_path):
        """Generate Japanese speech using OpenAI TTS API"""
        segments = self.split_by_speaker(japanese_text)
        combined_audio = None
        temp_files = []

        try:
            for segment in segments:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                    response = self.client.audio.speech.create(
                        model=self.tts_model,
                        voice="nova" if segment['speaker'] == 'A' else "shimmer",
                        input=segment['text']
                    )
                    temp_file.write(response.content)
                    temp_files.append(temp_file.name)

                    segment_audio = AudioSegment.from_mp3(temp_file.name)
                    if combined_audio is None:
                        combined_audio = segment_audio
                    else:
                        combined_audio += segment_audio

            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            combined_audio.export(output_path, format="mp3")

        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass

    def generate_html(self, japanese_text, output_path):
        """Generate HTML file from Japanese transcript using the template"""
        # Read the template file
        template_path = os.path.join(os.path.dirname(__file__), "templates", "templates.html")
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()

        # Create prompt for GPT to generate HTML
        prompt = f"""以下のテンプレートHTMLと会話文から、HTMLファイルを生成してください。

テンプレートHTML:
{template_content}

会話文:
{japanese_text}

要件：
1. テンプレートの構造とスタイルを維持しながら、以下の部分を会話内容に基づいて最適化してください：

   a) ヘッダー部分：
      - タイトル：会話内容を端的に表す適切なタイトルと、内容に合った絵文字を設定
      - ポッドキャストの種類：
        - 会話の形式を具体的に分析（例：「政策分析ニュース」「経済ニュース解説」「テクノロジートーク」など）
        - 「🎧 xxxxポッドキャスト」の部分を「🎧 [具体的なポッドキャスト名]」に置換
      - 出演者：
        - 「👥 話者A & 話者B」という形式ではなく
        - 「👥 話者A(政策アナリスト) & 話者B(経済評論家)」のように
        - 各話者の具体的な役割や肩書きを会話内容から分析して記載
      - トピック：
        - 会話の主要なトピックを具体的に抽出
        - 各トピックに最適な絵文字を付与

   b) 会話部分：
      - [話者A]の発言 → message-aクラスで左側に配置
      - [話者B]の発言 → message-bクラスで右側に配置
      - 話者Aのアイコン → fa-user
      - 話者Bのアイコン → fa-robot
      - speaker-roleクラス → 分析した具体的な役割を設定（例：「政策アナリスト」「経済評論家」）

2. 出力形式：
   - HTMLコードのみを出力（説明文は不要）
   - テンプレートのスタイルとスクリプトはそのまま維持

重要な注意点：
- 「xxxx」のような仮の文字列は使用せず、必ず会話内容から具体的な情報を抽出して置換してください
- 話者の役割は会話の文脈から具体的に推測し、一般的な「ホスト」「ゲスト」ではなく、専門性や立場が分かる表現にしてください
- ポッドキャストの種類も具体的なものにしてください（例：「ニュース解説」ではなく「国際政治ニュース解説」など）

会話内容を詳細に分析し、具体的で適切な情報をHTMLに組み込んでください。"""

        response = self.client.chat.completions.create(
            model=self.html_generation_model,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        html_content = response.choices[0].message.content.strip()
        
        # HTMLタグの前後の説明文を削除
        html_content = re.sub(r'^.*?<!DOCTYPE', '<!DOCTYPE', html_content, flags=re.DOTALL)
        html_content = re.sub(r'</html>.*$', '</html>', html_content, flags=re.DOTALL)

        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save the generated HTML
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def generate_output_filename(self, input_filename):
        """Generate output filenames for mp3 and html files"""
        base_name = os.path.splitext(os.path.basename(input_filename))[0]
        output_dir = os.path.join(os.path.dirname(__file__), "output")
        return (
            os.path.join(output_dir, f"{base_name}.mp3"),
            os.path.join(output_dir, f"{base_name}.html")
        )

def main():
    parser = argparse.ArgumentParser(description='英語音声を日本語音声に変換するツール')
    parser.add_argument('input_file', help='入力音声ファイル（MP3形式）')
    args = parser.parse_args()

    translator = AudioTranslator()
    
    # Convert mp3 to wav for processing
    input_wav = "temp_input.wav"
    audio = AudioSegment.from_mp3(args.input_file)
    audio.export(input_wav, format="wav")

    try:
        # Generate output filenames
        output_mp3, output_html = translator.generate_output_filename(args.input_file)

        # Process the audio
        print("音声をテキストに変換中...")
        english_text = translator.transcribe_audio(input_wav)
        
        print("日本語に翻訳中...")
        japanese_text = translator.translate_to_japanese(english_text)
        print("=japanese_text=",japanese_text)
        print("日本語音声を生成中...")
        translator.generate_japanese_audio(japanese_text, output_mp3)
        
        print("HTMLファイルを生成中...")
        translator.generate_html(japanese_text, output_html)
        
        print(f"変換が完了しました。")
        print(f"音声ファイル: {output_mp3}")
        print(f"HTMLファイル: {output_html}")

    finally:
        # Clean up temporary wav file
        if os.path.exists(input_wav):
            os.remove(input_wav)

if __name__ == "__main__":
    main()