# AWS SAM テンプレート リファレンス（3～6章）

> **関連ドキュメント**：[← 入門ガイド（0～2章）](./SAM_入門ガイド.md) | [コマンド・トラブルシューティング（7～10章）→](./SAM_コマンド_トラブルシューティング.md)

## 3. template.yaml の全体構造

`template.yaml` は、主に以下のセクションで構成されます。

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Description: >
  AWS SAM sample project

Globals:
  Function:
    Runtime: python3.13
    Timeout: 30

Mappings:
  EnvironmentMap:
    dev:
      LogLevel: DEBUG
    prd:
      LogLevel: INFO

Parameters:
  ResourcePrefix:
    Type: String
    Default: as

  Environment:
    Type: String
    Default: dev
    AllowedValues:
      - dev
      - prd

  ProjectName:
    Type: String
    Default: sam-project

Conditions:
  IsProduction: !Equals [!Ref Environment, prd]

Resources:
  SamProjectDataBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub ${ResourcePrefix}-${Environment}-${ProjectName}-data-${AWS::AccountId}

Outputs:
  DataBucketName:
    Value: !Ref SamProjectDataBucket
```

---

## 4. template.yaml 各セクション詳細

### 4.1 AWSTemplateFormatVersion

```yaml
AWSTemplateFormatVersion: '2010-09-09'
```

CloudFormationテンプレートのフォーマットバージョンです。通常は `'2010-09-09'` を使用します。

---

### 4.2 Transform

```yaml
Transform: AWS::Serverless-2016-10-31
```

SAM（Serverless Application Model）の変換を有効化する宣言です。

この1行があることで、`AWS::Serverless::Function` などのSAMリソースを使用できます。

---

### 4.3 Description

```yaml
Description: >
  AWS SAM sample project
```

テンプレートの説明文です。

`>` はYAMLの折りたたみブロック（folded block）で、複数行の文字列を1つの文字列として記述できます。

---

### 4.4 Globals（グローバル設定）

```yaml
Globals:
  Function:
    Timeout: 30
    MemorySize: 256
    Runtime: python3.13
```

`Globals` に書いた設定は、対象となるSAMリソースへ共通設定として適用されます。

個別のLambda関数で同じ項目を指定した場合は、個別設定が優先されます。

```yaml
Globals:
  Function:
    MemorySize: 256

Resources:
  SamProjectFunctions:
    Type: AWS::Serverless::Function
    Properties:
      MemorySize: 1024
```

Lambda Layerも共通化できます。

```yaml
Globals:
  Function:
    Layers:
      - !Ref SamProjectFunctionsLayer
```

> すべての関数で同じLayerを使う場合は `Globals.Function.Layers` にまとめると重複を減らせます。

---

### 4.5 Mappings（マッピング）

```yaml
Mappings:
  EnvironmentMap:
    dev:
      LogLevel: DEBUG
    prd:
      LogLevel: INFO
```

環境などに応じて固定値を切り替えるための対応表です。

値を参照するときは `!FindInMap` を使います。

```yaml
LOG_LEVEL: !FindInMap [EnvironmentMap, !Ref Environment, LogLevel]

# Environment = dev → DEBUG
# Environment = prd → INFO
```

> **Parametersとの違い**
>
> - `Parameters`：デプロイ時に外から値を渡す
> - `Mappings`：テンプレート内に固定の対応表を持つ

---

### 4.6 Parameters（パラメータ）

```yaml
Parameters:
  ResourcePrefix:
    Type: String
    Default: as
    AllowedPattern: "^[a-z0-9-]+$"

  Environment:
    Type: String
    Default: dev
    AllowedValues:
      - dev
      - prd

  ProjectName:
    Type: String
    Default: sam-project
    AllowedPattern: "^[a-z0-9-]+$"
```

デプロイ時に外から値を渡せる変数定義です。`samconfig.toml` の `parameter_overrides` や `sam deploy --parameter-overrides` で値を上書きできます。

| プロパティ | 説明 |
| --- | --- |
| `Type` | データ型 |
| `Default` | デフォルト値 |
| `AllowedValues` | 入力を特定の値に制限 |
| `AllowedPattern` | 正規表現で入力パターンを制限 |
| `Description` | パラメータの説明 |

```yaml
BucketName: !Sub ${ResourcePrefix}-${Environment}-${ProjectName}-data-${AWS::AccountId}
# → as-dev-sam-project-data-123456789012
```

---

### 4.7 Conditions（条件）

```yaml
Conditions:
  IsProduction: !Equals [!Ref Environment, prd]
```

特定の条件を満たす場合にのみリソースを作成したり、値を切り替えたりするための定義です。

| 関数 | 説明 |
| --- | --- |
| `!Equals [A, B]` | AとBが等しければ `true` |
| `!Not [条件]` | 条件を反転 |
| `!And [条件1, 条件2]` | すべて `true` なら `true` |
| `!Or [条件1, 条件2]` | いずれかが `true` なら `true` |

```yaml
PointInTimeRecoverySpecification:
  PointInTimeRecoveryEnabled: !If [IsProduction, true, false]
```

`Conditions` はリソース全体の作成有無だけでなく、`!If` と組み合わせてプロパティ値を切り替える用途にも使えます。

---

### 4.8 Resources（リソース定義）

`template.yaml` の中で、実際にAWS上へ作成するリソースを定義する必須セクションです。

```yaml
Resources:
  SamProjectFunctions:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub ${ResourcePrefix}-${Environment}-${ProjectName}-api-function
      # ...
```

**論理ID**（`SamProjectFunctions`）はPascalCase、AWS上へ明示的に付ける物理リソース名はlowercase kebab-caseに統一します。

---

### 4.9 Outputs（出力）

```yaml
Outputs:
  DataBucketName:
    Value: !Ref SamProjectDataBucket
    Description: データ保存用S3バケット名

  ApiUrl:
    Value: !Sub "https://${SamProjectApi}.execute-api.${AWS::Region}.${AWS::URLSuffix}/${Environment}/"
    Description: API Gateway URL
```

`sam deploy` 完了後にAWSコンソールやCLIから確認できる値です。

---

## 5. Resources 各リソースの詳細

### 5.1 S3 バケット

```yaml
SamProjectDataBucket:
  Type: AWS::S3::Bucket
  Properties:
    # S3バケット名は一意になりやすいようAWSアカウントIDを末尾に付ける
    BucketName: !Sub ${ResourcePrefix}-${Environment}-${ProjectName}-data-${AWS::AccountId}

    PublicAccessBlockConfiguration:
      BlockPublicAcls: true
      BlockPublicPolicy: true
      IgnorePublicAcls: true
      RestrictPublicBuckets: true

    CorsConfiguration:
      CorsRules:
        - Id: ApplicationAccess
          AllowedHeaders:
            - "*"
          AllowedMethods:
            - GET
            - PUT
          AllowedOrigins:
            - "*"  # 本番では必要なオリジンに限定する

    Tags:
      - Key: Project
        Value: !Ref ProjectName
      - Key: Environment
        Value: !Ref Environment
```

> **CORS（Cross-Origin Resource Sharing）とは**  
> ブラウザから異なるオリジンへリクエストする際に、許可するオリジン・HTTPメソッド・ヘッダーを制御する仕組みです。

> **署名付きURL（Pre-signed URL）とは**  
> S3への一時的なアクセス権を持つURLです。バックエンドで生成し、フロントエンドからS3へ直接アップロードする構成などで利用できます。

---

### 5.2 IAM Role（ロール）

IAM Roleは、**AWSサービスがどの権限を使って動作するか**を定義するために利用します。

```yaml
SamProjectFunctionsRole:
  Type: AWS::IAM::Role
  Properties:
    RoleName: !Sub ${ResourcePrefix}-${Environment}-${ProjectName}-lambda-role

    AssumeRolePolicyDocument:
      Version: "2012-10-17"
      Statement:
        - Effect: Allow
          Principal:
            Service:
              - lambda.amazonaws.com
          Action:
            - sts:AssumeRole

    ManagedPolicyArns:
      - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      - !Ref SamProjectFunctionsPolicy
```

> LambdaをVPCへ接続する場合は、ENI操作に必要な権限も追加します。VPC接続しないLambdaへVPC用権限を常に付ける必要はありません。

---

### 5.3 IAM ManagedPolicy（ポリシー）

ポリシーは、**どのリソースに対して、どの操作を許可・拒否するか**を定義します。

```yaml
SamProjectFunctionsPolicy:
  Type: AWS::IAM::ManagedPolicy
  Properties:
    ManagedPolicyName: !Sub ${ResourcePrefix}-${Environment}-${ProjectName}-lambda-policy

    PolicyDocument:
      Version: "2012-10-17"
      Statement:
        - Sid: S3ObjectAccess
          Effect: Allow
          Action:
            - s3:GetObject
            - s3:PutObject
          Resource:
            - !Sub "${SamProjectDataBucket.Arn}/*"

        - Sid: S3BucketAccess
          Effect: Allow
          Action:
            - s3:ListBucket
          Resource:
            - !GetAtt SamProjectDataBucket.Arn

        - Sid: DynamoDBAccess
          Effect: Allow
          Action:
            - dynamodb:GetItem
            - dynamodb:PutItem
            - dynamodb:UpdateItem
            - dynamodb:DeleteItem
            - dynamodb:Query
          Resource:
            - !GetAtt SamProjectDataTable.Arn
            - !Sub "${SamProjectDataTable.Arn}/index/*"
```

> **最小権限の原則**  
> `s3:*` のような全操作ではなく、アプリケーションで必要なActionとResourceだけを許可します。

---

### 5.4 API Gateway（Serverless::Api）

REST APIのエンドポイントを定義します。

```yaml
SamProjectApi:
  Type: AWS::Serverless::Api
  Properties:
    Name: !Sub ${ResourcePrefix}-${Environment}-${ProjectName}-api
    StageName: !Ref Environment

    EndpointConfiguration:
      Type: REGIONAL

    Description: SAM sample REST API

    Cors:
      AllowMethods: "'POST,OPTIONS,GET,PUT,DELETE'"
      AllowHeaders: "'Authorization,Content-Type,X-Amz-Date,X-Amz-Security-Token'"
      AllowOrigin: "'*'"

    MethodSettings:
      - LoggingLevel: INFO
        DataTraceEnabled: false
        MetricsEnabled: true
        ResourcePath: "/*"
        HttpMethod: "*"

    Tags:
      Project: !Ref ProjectName
      Environment: !Ref Environment
```

> **ステージ（Stage）とは**  
> API Gatewayのデプロイ単位です。この教材では環境名と合わせ、`dev` / `prd` を使用します。

> **`DataTraceEnabled` の注意点**  
> `true` にするとリクエストやレスポンスの詳細がログへ記録されます。機密情報やログ料金を考慮し、必要な場合のみ有効化します。

#### EndpointConfiguration（エンドポイントタイプ）の選び方

| タイプ | 説明 | 典型的な用途 |
| --- | --- | --- |
| `EDGE` | API Gatewayが管理するCloudFront経由で配信 | 地理的に分散したクライアント向けのパブリックAPI |
| `REGIONAL` | 指定リージョンにデプロイ | 一般的なリージョナルAPI、独自CloudFrontを前段に置く構成 |
| `PRIVATE` | Interface VPC Endpoint経由でアクセス | VPCやプライベートネットワークからのみ利用するAPI |

`Lambda` のVPC接続有無とAPI GatewayのEndpoint Typeは別の設計要素です。

---

### 5.5 Lambda Layer（Serverless::LayerVersion）

複数のLambda関数で共通して使うライブラリやコードを分離して管理できます。

```yaml
SamProjectFunctionsLayer:
  Type: AWS::Serverless::LayerVersion
  Properties:
    Description: 共通Pythonライブラリ
    LayerName: !Sub ${ResourcePrefix}-${Environment}-${ProjectName}-common-layer
    ContentUri: layers/common/
    CompatibleRuntimes:
      - python3.13

  Metadata:
    BuildMethod: python3.13
```

```yaml
SamProjectFunctions:
  Type: AWS::Serverless::Function
  Properties:
    Layers:
      - !Ref SamProjectFunctionsLayer
```

> `requests` や `aws-lambda-powertools` など、複数関数で共有したい依存ライブラリをLayerへまとめる方法があります。

---

### 5.6 Lambda関数（Serverless::Function）

```yaml
SamProjectFunctions:
  Type: AWS::Serverless::Function
  Properties:
    Runtime: python3.13
    Handler: app.lambda_handler
    Role: !GetAtt SamProjectFunctionsRole.Arn
    CodeUri: src/api/

    Description: SAM sample API function
    FunctionName: !Sub ${ResourcePrefix}-${Environment}-${ProjectName}-api-function

    Layers:
      - !Ref SamProjectFunctionsLayer

    Architectures:
      - x86_64

    Events:
      GetItems:
        Type: Api
        Properties:
          RestApiId: !Ref SamProjectApi
          Path: /items
          Method: GET

      CreateItem:
        Type: Api
        Properties:
          RestApiId: !Ref SamProjectApi
          Path: /items
          Method: POST

    Environment:
      Variables:
        BUCKET_NAME: !Ref SamProjectDataBucket
        TABLE_NAME: !Ref SamProjectDataTable
        POWERTOOLS_SERVICE_NAME: !Ref ProjectName
        LOG_LEVEL: !FindInMap [EnvironmentMap, !Ref Environment, LogLevel]

    Tags:
      Project: !Ref ProjectName
      Environment: !Ref Environment
```

> **Handlerについて**  
> `app.lambda_handler` は「`app.py` の `lambda_handler` 関数を実行する」という意味です。

> **EventsのTypeについて**
> - `Api`：API Gateway REST API
> - `Schedule`：定期実行
> - `S3`：S3イベント
> - `DynamoDB`：DynamoDB Streams
> - `SQS`：SQSキュー

> **Architectureについて**  
> `x86_64` と `arm64` を選択できます。`arm64` を利用する場合は依存ライブラリの対応状況も確認します。

#### スケジュール実行のLambda

```yaml
SamProjectScheduledProcessor:
  Type: AWS::Serverless::Function
  Properties:
    FunctionName: !Sub ${ResourcePrefix}-${Environment}-${ProjectName}-scheduled-processor
    Runtime: python3.13
    Handler: app.lambda_handler
    CodeUri: src/scheduled/

    Events:
      ScheduleEvent:
        Type: Schedule
        Properties:
          Schedule: rate(1 hour)
          Name: !Sub ${ResourcePrefix}-${Environment}-${ProjectName}-schedule
          Description: 1時間ごとのサンプル定期処理
          Enabled: true
```

---

### 5.7 DynamoDB テーブル

```yaml
SamProjectDataTable:
  Type: AWS::DynamoDB::Table
  Properties:
    TableName: !Sub ${ResourcePrefix}-${Environment}-${ProjectName}-data-table
    BillingMode: PAY_PER_REQUEST

    AttributeDefinitions:
      - AttributeName: PK
        AttributeType: S
      - AttributeName: SK
        AttributeType: S

    KeySchema:
      - AttributeName: PK
        KeyType: HASH
      - AttributeName: SK
        KeyType: RANGE

    PointInTimeRecoverySpecification:
      PointInTimeRecoveryEnabled: !If [IsProduction, true, false]

    Tags:
      - Key: Project
        Value: !Ref ProjectName
      - Key: Environment
        Value: !Ref Environment
```

> **パーティションキー（PK）とソートキー（SK）**  
> パーティションキーだけ、またはパーティションキーとソートキーの組み合わせでアイテムを識別します。

> **BillingModeの選び方**
> - `PAY_PER_REQUEST`：アクセス量を予測しにくい場合や運用を簡単にしたい場合
> - `PROVISIONED`：必要な読み書きキャパシティを事前に設定したい場合

#### DynamoDB（PROVISIONEDモード）の例

```yaml
SamProjectProvisionedTable:
  Type: AWS::DynamoDB::Table
  Properties:
    TableName: !Sub ${ResourcePrefix}-${Environment}-${ProjectName}-provisioned-table

    AttributeDefinitions:
      - AttributeName: PK
        AttributeType: S

    KeySchema:
      - AttributeName: PK
        KeyType: HASH

    BillingMode: PROVISIONED
    ProvisionedThroughput:
      ReadCapacityUnits: 5
      WriteCapacityUnits: 5
```

`ReadCapacityUnits` / `WriteCapacityUnits` は単純な「1秒あたりのリクエスト回数」ではなく、アイテムサイズや読み取り整合性などによって消費量が変わります。

#### DynamoDB GSI（グローバルセカンダリインデックス）

```yaml
SamProjectIndexedTable:
  Type: AWS::DynamoDB::Table
  Properties:
    TableName: !Sub ${ResourcePrefix}-${Environment}-${ProjectName}-indexed-table
    BillingMode: PAY_PER_REQUEST

    AttributeDefinitions:
      - AttributeName: PK
        AttributeType: S
      - AttributeName: SK
        AttributeType: S
      - AttributeName: GSI1PK
        AttributeType: S
      - AttributeName: GSI1SK
        AttributeType: S

    KeySchema:
      - AttributeName: PK
        KeyType: HASH
      - AttributeName: SK
        KeyType: RANGE

    GlobalSecondaryIndexes:
      - IndexName: gsi1
        KeySchema:
          - AttributeName: GSI1PK
            KeyType: HASH
          - AttributeName: GSI1SK
            KeyType: RANGE
        Projection:
          ProjectionType: ALL
```

> PROVISIONEDモードでGSIを使う場合は、GSI側にも `ProvisionedThroughput` の設定が必要です。

---

### 5.8 Cognito

Amazon Cognito User Poolsは、Webアプリケーションなどのユーザー認証・ユーザーディレクトリ機能を提供します。

この章では特定のIdPや特定システムの運用手順ではなく、Cognitoの基本要素を説明します。

```yaml
SamProjectUserPool:
  Type: AWS::Cognito::UserPool
  Properties:
    UserPoolName: !Sub ${ResourcePrefix}-${Environment}-${ProjectName}-users

    UsernameAttributes:
      - email

    AutoVerifiedAttributes:
      - email

    UsernameConfiguration:
      CaseSensitive: false

    Policies:
      PasswordPolicy:
        MinimumLength: 12
        RequireUppercase: true
        RequireLowercase: true
        RequireNumbers: true
        RequireSymbols: true
```

#### Cognitoユーザープールドメイン

```yaml
SamProjectUserPoolDomain:
  Type: AWS::Cognito::UserPoolDomain
  Properties:
    Domain: !Sub ${ResourcePrefix}-${Environment}-${ProjectName}-${AWS::AccountId}
    UserPoolId: !Ref SamProjectUserPool
```

Cognitoのマネージドログインを利用する場合などにドメインを設定します。

#### Cognitoアプリクライアント

```yaml
SamProjectAppClient:
  Type: AWS::Cognito::UserPoolClient
  Properties:
    ClientName: !Sub ${ResourcePrefix}-${Environment}-${ProjectName}-web-client
    UserPoolId: !Ref SamProjectUserPool

    # SPAなどのPublic Clientではクライアントシークレットを保持しない
    GenerateSecret: false
    PreventUserExistenceErrors: ENABLED
    EnableTokenRevocation: true

    CallbackURLs:
      - http://localhost:5173/

    LogoutURLs:
      - http://localhost:5173/

    AllowedOAuthFlowsUserPoolClient: true
    AllowedOAuthFlows:
      - code
    AllowedOAuthScopes:
      - openid
      - email
    SupportedIdentityProviders:
      - COGNITO
```

> **Authorization Code Flow + PKCE**  
> SPAのようにクライアントシークレットを安全に保持できないPublic Clientでは、Authorization Code FlowとPKCEを組み合わせる構成が一般的です。`GenerateSecret: false` とし、フロントエンド側でPKCEを扱います。

#### 外部SAML IdPとの連携例

Cognito User Poolは、SAML 2.0に対応した外部IdPと連携できます。

以下は**仕組みを理解するための一般化した例**です。実際のメタデータURL、属性マッピング、Callback URLなどは利用するIdPとシステム要件に合わせて設定します。

```yaml
Parameters:
  SamlMetadataUrl:
    Type: String
    Description: SAML IdPのメタデータURL

Resources:
  SamProjectSamlIdentityProvider:
    Type: AWS::Cognito::UserPoolIdentityProvider
    Properties:
      UserPoolId: !Ref SamProjectUserPool
      ProviderName: ExampleSamlIdP
      ProviderType: SAML
      ProviderDetails:
        MetadataURL: !Ref SamlMetadataUrl
```

アプリクライアントで外部IdPを利用する場合は、`SupportedIdentityProviders` にProviderNameを追加します。

```yaml
SupportedIdentityProviders:
  - COGNITO
  - ExampleSamlIdP
```

> 外部IdPとの連携では、IdP側とCognito側の双方に設定が必要です。設定順序や自動化方法はIdP・組織・デプロイ方式によって異なるため、この教材では特定の段階的デプロイ手順には固定しません。

#### Cognitoまとめ

| リソース | 役割 |
| --- | --- |
| `AWS::Cognito::UserPool` | ユーザーディレクトリ・認証基盤 |
| `AWS::Cognito::UserPoolDomain` | マネージドログインなどで使用するドメイン |
| `AWS::Cognito::UserPoolClient` | WebアプリなどがCognitoを利用するためのクライアント |
| `AWS::Cognito::UserPoolIdentityProvider` | 外部SAML/OIDC IdPとの連携 |

---

### 5.9 CloudFront（S3 + CloudFront によるSPAホスティング）

SPAをS3に配置する場合、S3を直接パブリック公開せず、CloudFrontを経由して配信する構成を利用できます。

```text
ユーザー
   ↓ HTTPS
CloudFront
   ↓ OACで署名
S3バケット（非公開）
   ├─ index.html
   └─ assets/
```

#### SamProjectFrontendBucket（S3バケット）

```yaml
SamProjectFrontendBucket:
  Type: AWS::S3::Bucket
  Properties:
    # S3バケット名は一意になりやすいようAWSアカウントIDを末尾に付ける
    BucketName: !Sub ${ResourcePrefix}-${Environment}-${ProjectName}-frontend-${AWS::AccountId}

    PublicAccessBlockConfiguration:
      BlockPublicAcls: true
      BlockPublicPolicy: true
      IgnorePublicAcls: true
      RestrictPublicBuckets: true
```

#### SamProjectFrontendBucketPolicy（S3 Bucket Policy）

```yaml
SamProjectFrontendBucketPolicy:
  Type: AWS::S3::BucketPolicy
  Properties:
    Bucket: !Ref SamProjectFrontendBucket
    PolicyDocument:
      Version: "2012-10-17"
      Statement:
        - Effect: Allow
          Principal:
            Service: cloudfront.amazonaws.com
          Action:
            - s3:GetObject
          Resource: !Sub "${SamProjectFrontendBucket.Arn}/*"
          Condition:
            StringEquals:
              AWS:SourceArn: !Sub "arn:aws:cloudfront::${AWS::AccountId}:distribution/${SamProjectFrontendDistribution}"
```

CloudFrontサービスへ `s3:GetObject` を許可し、`AWS:SourceArn` で対象Distributionを限定します。

#### SamProjectFrontendOAC（Origin Access Control）

```yaml
SamProjectFrontendOAC:
  Type: AWS::CloudFront::OriginAccessControl
  Properties:
    OriginAccessControlConfig:
      Name: !Sub ${ResourcePrefix}-${Environment}-${ProjectName}-oac
      OriginAccessControlOriginType: s3
      SigningBehavior: always
      SigningProtocol: sigv4
```

OACは、CloudFrontから非公開S3バケットへアクセスするための仕組みです。

#### SamProjectFrontendDistribution（CloudFront Distribution）

```yaml
SamProjectFrontendDistribution:
  Type: AWS::CloudFront::Distribution
  Properties:
    DistributionConfig:
      Enabled: true
      DefaultRootObject: index.html

      Origins:
        - Id: FrontendS3Origin
          DomainName: !GetAtt SamProjectFrontendBucket.RegionalDomainName
          OriginAccessControlId: !GetAtt SamProjectFrontendOAC.Id
          S3OriginConfig: {}

      DefaultCacheBehavior:
        TargetOriginId: FrontendS3Origin
        ViewerProtocolPolicy: redirect-to-https
        AllowedMethods:
          - GET
          - HEAD
        CachedMethods:
          - GET
          - HEAD
        CachePolicyId: 658327ea-f89d-4fab-a63d-7e88639e58f6
        Compress: true

      CustomErrorResponses:
        - ErrorCode: 403
          ResponseCode: 200
          ResponsePagePath: /index.html
        - ErrorCode: 404
          ResponseCode: 200
          ResponsePagePath: /index.html
```

S3にはビルド成果物をルートから配置する例とします。

```text
S3バケット
├─ index.html
└─ assets/
    ├─ index-xxxx.js
    └─ index-xxxx.css
```

#### CachePolicyId

`658327ea-f89d-4fab-a63d-7e88639e58f6` はAWS管理の **CachingOptimized** ポリシーのIDです。

新しいバージョンを即時反映したい場合は、ファイル名へハッシュを付ける運用やCloudFront Invalidationを組み合わせます。

#### SPAのルーティング対応

Vue RouterやReact RouterなどでHistory Modeを使う場合、直接アクセスしたパスに対応するS3オブジェクトが存在しないことがあります。

この例では `CustomErrorResponses` を使い、403 / 404時に `index.html` を返します。

> すべての403 / 404を200へ変換するため、要件に応じてルーティング方式を検討してください。

#### Outputs

```yaml
Outputs:
  FrontendBucketName:
    Description: フロントエンドS3バケット名
    Value: !Ref SamProjectFrontendBucket

  CloudFrontDomain:
    Description: CloudFrontディストリビューションドメイン
    Value: !GetAtt SamProjectFrontendDistribution.DomainName

  CloudFrontDistributionId:
    Description: CloudFront Distribution ID
    Value: !Ref SamProjectFrontendDistribution
```

---

## 6. 組み込み関数（!Sub、!Ref、!GetAtt など）

CloudFormationには、値を動的に取得・組み立てるための組み込み関数があります。

### !Ref（リソースやパラメータを参照）

```yaml
# パラメータを参照
Value: !Ref Environment
# → dev

# リソースを参照
Value: !Ref SamProjectDataTable
# → DynamoDBテーブル名
```

`!Ref` が返す値はリソースタイプによって異なります。

### !GetAtt（リソースの属性を取得）

```yaml
Resource: !GetAtt SamProjectDataBucket.Arn
# → arn:aws:s3:::as-dev-sam-project-data-123456789012

Role: !GetAtt SamProjectFunctionsRole.Arn
# → arn:aws:iam::123456789012:role/as-dev-sam-project-lambda-role
```

### !Sub（文字列に変数を埋め込む）

```yaml
BucketName: !Sub ${ResourcePrefix}-${Environment}-${ProjectName}-data-${AWS::AccountId}
# → as-dev-sam-project-data-123456789012

Resource: !Sub "arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/my-table"
# → arn:aws:dynamodb:ap-northeast-1:123456789012:table/my-table
```

> **擬似パラメータ（AWS::XXXX）**
> - `${AWS::Region}`：リージョン名
> - `${AWS::AccountId}`：AWSアカウントID
> - `${AWS::StackName}`：スタック名
> - `${AWS::URLSuffix}`：AWS URLサフィックス

### !FindInMap（Mappingsから値を取得）

```yaml
LogLevel: !FindInMap [EnvironmentMap, !Ref Environment, LogLevel]
```

`Mappings` の指定したキーから値を取得します。

### !If（条件分岐）

```yaml
Value: !If [IsProduction, "production", "development"]

OptionalValue: !If
  - IsProduction
  - "enabled"
  - !Ref AWS::NoValue
```

`!Ref AWS::NoValue` は、条件に応じてプロパティや値を削除するときに利用します。
