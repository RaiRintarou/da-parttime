# Shift Optimiser – Improvement Roadmap (Rev. 2025-06-29)

> **Goal:** Streamlit PoC を 2025 Q3 までに 1 サイトで試験稼働できるセキュアな MVP へ、さらに 2026 Q1 に全社ロールアウト可能な Scale 版へ拡張する。

---

## Phase 0 – PoC Hardening (~2025 Jul)
### 0.1 Core Logic Stabilisation
- [x] 単一タイムブロック → Multi-slot 日次モデル へリファクタ（ユニットテスト付き）
  - ✅ Multi-slotデータ構造の実装
  - ✅ TimeSlot, DailySchedule, OperatorAvailabilityクラス
  - ✅ DeskRequirement, Assignmentクラス
  - ✅ MultiSlotSchedulerクラス
  - ✅ 21個のユニットテスト実装
  - ✅ 従来モデルとの変換機能
  - ✅ プロジェクト構造の整理（src/ディレクトリ構成）
  - ✅ Poetry対応の依存関係管理
  - ✅ メインエントリーポイント（main.py）の実装
  - ✅ Makefileによる開発支援コマンド
- [x] **Hard constraint DSL** のスケルトン実装（最小休息・連勤上限等）
  - ✅ 制約の基本クラスと具体的な制約クラス実装
  - ✅ MinRestHoursConstraint, MaxConsecutiveDaysConstraint
  - ✅ MaxWeeklyHoursConstraint, MaxNightShiftsPerWeekConstraint
  - ✅ RequiredDayOffAfterNightConstraint
  - ✅ ConstraintParser, ConstraintValidator実装
  - ✅ 制約付きMulti-slot DAアルゴリズム統合
  - ✅ Streamlitアプリへの制約チェック機能追加
  - ✅ 制約違反検出と警告表示機能

### 0.2 Ops & QA
- [x] `pytest` 導入・GitHub Actions で **CI テンプレート**（coverage>60%）
- [x] **Dockerfile（dev）** 作成、VS Code Dev Container 対応  
- [x] **PoC 環境用 secrets** を `.env` + direnv で集中管理

---

## Phase 1 – MVP for Single-Site Pilot (~2025 Oct)
### 1.1 Data Layer & Integrations
- [ ] **SQLite → Postgres 移行**：Workers / Shifts / Assignments / Rules スキーマ確定
- [ ] **CSV ⇄ DB インポート／エクスポート** コマンド（CLI & UI）
- [ ] **HRIS ワンウェイ同期 (Workday)**：基本属性 + 勤務区分のみ

### 1.2 Scheduling Engine Options
- [ ] **OR-Tools CP-SAT バックエンド** プラガブル化
- [ ] **オーバータイム上限**・**複数割当て**ルール実装（設定画面付き）

### 1.3 UI / UX
- [ ] **Streamlit AgGrid** に置換（1,000 rows 以上でも 200 ms 未満）
- [ ] **シナリオ複製 & 比較** 画面（サイドバイサイド diff）
- [ ] **EN/JP トグル & ダークモード** 初期実装

### 1.4 Security & Compliance
- [ ] **Azure AD SSO** + RBAC（Admin / Planner / Viewer）
- [ ] **監査ログ API**: who/what/when JSON line 出力
- [ ] **GDPR/J-PIPA データ保持ポリシー** ドキュメント化

### 1.5 Quality Assurance
- [ ] ユニットテスト coverage > 80 % & mutation test 実行
- [ ] **Playwright E2E**：ログイン〜シフト生成〜CSV DL まで
- [ ] **テスト用サンプルデータ 3 ケース**（小・中・大）

---

## Phase 2 – Pilot Feedback & Hardening (~2025 Dec)
### 2.1 Analytics
- [ ] **KPI Dashboard v1**：充足率・残業時間・フェアネス
- [ ] **What-if Simulation**：人員スライダー→リアルタイム再計算 (<3 s)

### 2.2 Collaboration
- [ ] **Slack / Teams 通知**：確定ロスター公開時
- [ ] **シフト交換ワークフロー v1**（申請→承認→自動再最適化）

### 2.3 Performance
- [ ] **ベンチマーク**：1 000 workers × 30 days → solver latency < 10 s
- [ ] **非同期バックグラウンド実行**：RQ + Redis、進捗バー UI

### 2.4 Deployment
- [ ] **Docker Compose (dev/stage/prod)** + **K8s Helm Chart** 雛形
- [ ] **GitHub Actions → GHCR→ Staging** 自動デプロイ

---

## Phase 3 – Company-wide Scale (~2026 Mar)
### 3.1 Advanced Optimisation
- [ ] **DA（量子アニーリング）バックエンド** PoC / fallback
- [ ] **スキル成長・減衰**タイムシリーズモデル + 学習率パラメータ

### 3.2 Mobile & UX++
- [ ] **モバイル PWA**：勤務表閲覧・休暇申請
- [ ] **ヒートマップ & ガントチャート** ビジュアライゼーション

### 3.3 Enterprise-grade Ops
- [ ] **Sentry / Grafana / Prometheus** 監視スタック
- [ ] **Load / Soak Test**：同時 200 planner + 10 000 worker アクセス

### 3.4 Documentation & Training
- [ ] **多言語 User Guide**（JP/EN/ES）+ 動画チュートリアル
- [ ] **Admin Playbook**：バックアップ、緊急ロールバック手順
- [ ] **アーキテクチャ図**（PlantUML）自動生成 CI

---

## Stretch / R&D Backlog
- [ ] **ML 需要予測** → シフト要件自動生成
- [ ] **強化学習プランナー**：ユーザーフィードバックで報酬学習
- [ ] **Gamification**：不人気シフトカバーでポイント付与
- [ ] **Explainable AI**：最適化結果の根拠提示 UI

---

### 使い方メモ（Cursor 向け）
1. この Markdown をリポジトリ直下の `ROADMAP.md` としてコミット。  
2. Cursor で「Split into Issues」を実行し、**Phase 0** → **Phase 3** をマイルストーンに自動割当。  
3. 依存関係は上から順に親子 Issue としてリンク。  
4. スプリント計画時に必要に応じて更にタスクを細分化。  

---
