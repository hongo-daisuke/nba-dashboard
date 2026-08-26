#!/bin/bash

echo "Creating AWS Lambda layer from requirements.txt..."

# 既存のフォルダを削除（クリーンスタート）
rm -rf python layer.zip

# python フォルダを作成
mkdir -p python

# requirements.txt からパッケージをインストール
python -m pip install --upgrade -r requirements.txt -t ./python

# zip ファイルを作成
zip -r9 layer.zip python

echo "Lambda layer created successfully: layer.zip"