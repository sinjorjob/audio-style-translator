# Audio Style Translator

英語の音声を日本語に翻訳し、異なる会話スタイル（ポッドキャスト、バラエティ番組、ニュースレポート）で出力するPythonツールです。OpenAIのAPIを使用して、音声認識、翻訳、音声合成を行います。

## 特徴

- 英語音声を日本語に翻訳
- 3つの会話スタイルをサポート：
  - ポッドキャスト形式：自然な対話形式
  - サンデージャポン形式：バラエティ番組風の掛け合い
  - ニュースレポート形式：フォーマルな報道調
- 2名の話者による会話形式で出力
- 音声ファイル（MP3）とトランスクリプト（HTML）を生成

## 必要条件

- Python 3.8以上
- OpenAI API キー
- 必要なPythonパッケージ（requirements.txtに記載）

## インストール

1. リポジトリをクローン：
```bash
git clone https://github.com/sinjorjob/audio-style-translator.git
cd audio-style-translator
```

2. 必要なパッケージをインストール：
```bash
pip install -r requirements.txt
```

3. 設定ファイルを編集：
   - `config.ini.example` を `config.ini` にリネーム
   - OpenAI APIキーを設定
   - 必要に応じて翻訳スタイルを変更

## 使用方法

1. 基本的な使用方法：
```bash
python audio_style_converter.py input.mp3
```

2. 出力ファイル：
   - 変換された音声: `output/[入力ファイル名].mp3`
   - トランスクリプト: `output/[入力ファイル名].html`

## 設定

`config.ini` で以下の設定が可能：

```ini
[OpenAI]
api_key = your-api-key

[Models]
transcription_model = whisper-1
translation_model = o1-mini
tts_model = tts-1
html_generation_model = gpt-4o-mini

[Translation]
# 選択可能: podcast, sunday_japon, news_report
style = news_report
```

## プロジェクト構造

```
audio-style-translator/
├── source/
│   ├── audio_style_converter.py  # メインスクリプト
│   ├── config.ini               # 設定ファイル
│   ├── requirements.txt         # 依存パッケージ
│   ├── output/                  # 出力ファイル保存ディレクトリ
│   └── templates/               # HTMLテンプレート
└── README.md
```


## 注意事項

- OpenAI APIの利用料金が発生します
- 大きな音声ファイルは自動的に分割して処理されます
- 処理時間は入力ファイルのサイズに応じて変動します

