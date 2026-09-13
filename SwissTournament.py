import streamlit as st
import random
import pandas as pd

# ページ設定
st.set_page_config(page_title="大会組み合わせシステム")

# --- セッションステート（状態の保存）の初期化 ---
if "players" not in st.session_state:
    st.session_state.players = []
if "phase" not in st.session_state:
    st.session_state.phase = "setup"  # "setup" または "swiss"
if "format" not in st.session_state:
    st.session_state.format = "スイス式トーナメント"
if "allow_draws" not in st.session_state:
    st.session_state.allow_draws = "あり"
if "round" not in st.session_state:
    st.session_state.round = 1
if "standings" not in st.session_state:
    st.session_state.standings = {}
if "history" not in st.session_state:
    st.session_state.history = {}
if "current_pairings" not in st.session_state:
    st.session_state.current_pairings = []
if "current_bye" not in st.session_state:
    st.session_state.current_bye = None
if "matchups_generated" not in st.session_state:
    st.session_state.matchups_generated = False

# --- 関数 ---
def calculate_opo(player):
    """オポ（対戦相手の勝ち点の合計）を計算"""
    opo = 0
    for opp in st.session_state.history[player]:
        if opp in st.session_state.standings:
            opo += st.session_state.standings[opp]["points"]
    return opo

def generate_swiss_pairings():
    """指定された手順①〜④に基づくスイス式の組み合わせ生成"""
    players = st.session_state.players
    standings = st.session_state.standings
    history = st.session_state.history

    # ④の「やり直し」が無限ループにならないよう最大試行回数を設定
    max_retries = 1000
    for _ in range(max_retries):
        available = list(players)
        bye = None

        # ①奇数の場合、一番小さい勝ち点の中からランダムに1人を不戦勝とする
        if len(available) % 2 != 0:
            min_pts = min([standings[p]["points"] for p in available])
            min_players = [p for p in available if standings[p]["points"] == min_pts]
            bye = random.choice(min_players)
            available.remove(bye)

        # ②勝ち点順に並べる（同じ勝ち点の中でランダム）
        pts_groups = {}
        for p in available:
            pts = standings[p]["points"]
            if pts not in pts_groups:
                pts_groups[pts] = []
            pts_groups[pts].append(p)

        sorted_available = []
        # 勝ち点が高い順に処理
        for pts in sorted(pts_groups.keys(), reverse=True):
            group = pts_groups[pts]
            random.shuffle(group) # 同じ勝ち点の中でランダム
            sorted_available.extend(group)

        # ③上から順に対戦相手とする ＆ ④過去の対戦チェック
        pairings = []
        valid = True
        for i in range(0, len(sorted_available), 2):
            p1 = sorted_available[i]
            p2 = sorted_available[i+1]
            if p2 in history[p1]: # 過去に対戦がある場合
                valid = False
                break
            pairings.append((p1, p2))

        # ④チェックを越えたら返す
        if valid:
            return pairings, bye

    # 1000回やり直しても決まらない場合（終盤などで全員が対戦済み等の場合）
    return None, None 

# --- UI (画面構成) ---
if st.session_state.phase == "setup":
    st.title("大会設定 (初期画面)")

    # 選手登録フォーム
    st.subheader("選手登録")
    col1, col2 = st.columns([3, 1])
    with col1:
        new_player = st.text_input("選手名を入力", key="new_player_input")
    with col2:
        # 見た目を合わせるための余白
        st.write("") 
        if st.button("登録"):
            if new_player and new_player not in st.session_state.players:
                st.session_state.players.append(new_player)
            elif new_player in st.session_state.players:
                st.warning("その選手は既に登録されています。")

    # 登録された選手の一覧表示
    if st.session_state.players:
        st.write(f"登録済みの選手（計 {len(st.session_state.players)}人）: ", " / ".join(st.session_state.players))

    # 大会形式
    st.subheader("大会形式")
    formats = [
        "スイス式トーナメント",
        "トーナメント",
        "トーナメント+負けトーナメント",
        "リーグ戦(総当たり)",
        "リーグ戦+トーナメント"
    ]
    selected_format = st.radio("形式を選択", formats)

    # 引き分けの有無（トーナメントとトーナメント+負けトーナメントを選択時は表示しない）
    allow_draws = "なし"
    if selected_format not in ["トーナメント", "トーナメント+負けトーナメント"]:
        st.subheader("引き分けの有無")
        allow_draws = st.radio("設定", ["あり", "なし"])

    # スタートボタン
    if st.button("大会スタート"):
        if len(st.session_state.players) < 2:
            st.error("選手を2名以上登録してください。")
        elif selected_format != "スイス式トーナメント":
            st.error("現在は「スイス式トーナメント」のみ実行可能です。")
        else:
            st.session_state.format = selected_format
            st.session_state.allow_draws = allow_draws
            # 成績の初期化
            for p in st.session_state.players:
                st.session_state.standings[p] = {"points": 0, "wins": 0, "losses": 0, "draws": 0}
                st.session_state.history[p] = set()
            st.session_state.phase = "swiss"
            st.rerun()

elif st.session_state.phase == "swiss":
    st.title(f"スイス式トーナメント (第{st.session_state.round}回戦)")

    # 組み合わせ決定ボタン
    if not st.session_state.matchups_generated:
        if st.button(f"第{st.session_state.round}回戦の組み合わせを決める"):
            pairings, bye = generate_swiss_pairings()
            if pairings is None and bye is None:
                st.error("条件を満たす組み合わせが見つかりませんでした（既に対戦相手がいない等）。")
            else:
                st.session_state.current_pairings = pairings
                st.session_state.current_bye = bye
                st.session_state.matchups_generated = True
                st.rerun()
    else:
        st.subheader("対戦表")
        
        # 結果入力フォーム
        with st.form("results_form"):
            results = {}
            for idx, (p1, p2) in enumerate(st.session_state.current_pairings):
                options = [f"▽ {p1}の勝利", f"▽ {p2}の勝利"]
                if st.session_state.allow_draws == "あり":
                    options.append("▽ 引き分け")
                
                # 対戦結果の選択
                res = st.selectbox(f"{p1} vs {p2} 結果:", options, key=f"match_{idx}")
                results[(p1, p2)] = res

            # 不戦勝の表示
            if st.session_state.current_bye:
                st.info(f"不戦勝: {st.session_state.current_bye}")

            submitted = st.form_submit_button("結果を確定して次の回戦へ")
            if submitted:
                # 結果を成績データに反映
                for (p1, p2), res in results.items():
                    # 履歴の追加
                    st.session_state.history[p1].add(p2)
                    st.session_state.history[p2].add(p1)
                    
                    if "の勝利" in res:
                        winner = p1 if p1 in res else p2
                        loser = p2 if p1 in res else p1
                        st.session_state.standings[winner]["wins"] += 1
                        st.session_state.standings[winner]["points"] += 3
                        st.session_state.standings[loser]["losses"] += 1
                    elif "引き分け" in res:
                        st.session_state.standings[p1]["draws"] += 1
                        st.session_state.standings[p1]["points"] += 1
                        st.session_state.standings[p2]["draws"] += 1
                        st.session_state.standings[p2]["points"] += 1

                # 不戦勝の処理（勝利扱いとし勝ち点3）
                if st.session_state.current_bye:
                    bye_p = st.session_state.current_bye
                    st.session_state.standings[bye_p]["wins"] += 1
                    st.session_state.standings[bye_p]["points"] += 3

                # ラウンドを進める
                st.session_state.round += 1
                st.session_state.matchups_generated = False
                st.rerun()

    st.markdown("---")
    st.subheader("順位表")
    
    # 順位表データの作成
    table_data = []
    for p in st.session_state.players:
        s = st.session_state.standings[p]
        opo = calculate_opo(p)
        table_data.append({
            "選手": p,
            "勝ち点": s["points"],
            "オポ": opo,
            "勝利": s["wins"],
            "敗北": s["losses"],
            "引分": s["draws"],
        })
    
    # 勝ち点 -> オポ の優先順位で並び替えて表示
    df = pd.DataFrame(table_data)
    if not df.empty:
        df = df.sort_values(by=["勝ち点", "オポ"], ascending=[False, False]).reset_index(drop=True)
        df.index = df.index + 1
        df.index.name = "順位"
        st.dataframe(df, use_container_width=True)
