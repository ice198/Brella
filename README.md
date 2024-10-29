# Brella v.1.5

人狼onlineで動作するbot。過去から現在までのログを集計し、プレイヤーのスキルをレート(人狼パワー)として数値化する。あまり当てにならない。

## セットアップ

#### 1. Chromeブラウザをインストール
すでにインストール済みの場合はスキップ

#### 2. VSCodeをインストール
[ダウンロードページ](https://code.visualstudio.com/download)からVSCodeを入れた後、BrellaフォルダをVSCodeで開く。
```
user@PC:~/Desktop/Brella$ 
```
ターミナルを表示させて、最後の文字列がBrellaになっていればOK

#### 3. Chromeドライバーをダウンロード
[このページ](https://googlechromelabs.github.io/chrome-for-testing/)からそれぞれのOSのchromeドライバー(**Stable**の**chromedriver**)をダウンロードしてBrellaフォルダ内のchromeフォルダに置く。
```
Brella
├── README.md
├── bot.py
├── chrome
│   └── chromedriver
├── data
└── settings.txt
```


#### 4. Pythonとpipをインストール
OSごとに方法が異なるため省略。

#### 5. 環境構築
pythonとpipがインストールできたら以下を実行

```py
python3  -m venv venv
```
次は使うOSによって異なる

Mac,Linuxの場合
```py
source venv/bin/activate
```
Windowsの場合
```py
.\venv\Scripts\activate
```
その後はどのOSも同じ
```py
pip install selenium
pip install pandas
pip install requests
 ```
 
 #### 6. 管理者設定
settings.txtの2行目に管理者のトリップを入力する。(初期に ◆example.AA となっている箇所を書き換える。)

2行目以外の場所に記述した場合は認識されないため注意。基本的に1回設定すれば変更する必要はないが、使うトリップを変えた場合はその都度変更する必要がある。

## 使い方
以下を実行
```py
python3 bot.py
```
chromeブラウザが自動実行されて村選択画面が表示されるので、自分が建てた村にbotを**観戦者**として入村させる。40秒ごとにページを読み込み直すので、ページが途中でリフレッシュされるまでに入村させる必要がある。(入村後にブラウザは自動で最小化される。)

入村後は自動で実行されるため操作する必要はない。botの機能を使うには以下のコマンドを人狼onlineのページで発言する。

### 一般コマンド
すべてのユーザーが使えるコマンド

**#ウデマエ**　　　内部レートをもとに S A B C の中から判定される
<br>**#タイマー** XX　 XXの部分に数字を入れる。#タイマー 30 だと30秒が計測される

ウデマエの仕様はプレイヤーのレートが全体の上位何％かで判定している。

S 上位20%以上
<br>A 上位50%以上
<br>B 上位50%未満
<br>C 人狼パワーが不明

レートは過去の10a狩のログを集計して計算している。平均は1500。

### 管理者コマンド
管理者のみが使えるコマンド

**#部屋パワー**　　　プレイヤーの平均内部レートを表示
<br>**#開始**　　　　　　botにゲームの開始を伝える
<br>**#退室**　　　　　　botを村から退出させる

