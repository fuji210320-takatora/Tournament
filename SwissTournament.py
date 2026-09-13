import streamlit as st
import random
import pandas as pd

# ページ設定
st.set_page_config(page_title="大会組み合わせシステム")

# --- セッションステートの初期化 ---
if "players" not in st.session_state:
    st.session_state.players = []
if "phase" not in st.session_state:
    st.session_state.phase = "setup"
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
if "defeated" not in st.session_state:
    st.session_state.defeated = {} # 勝手累点計算用（勝利した相手を記録）
if "current_pairings" not in st.session_state:
    st.session_state.current_pairings = []
if "current_bye" not in st.session_state:
    st.session_state.current_bye = None
if "matchups_generated" not in st.session_state:
    st.session_state.matchups_generated = False

# --- 関数 ---
def add_player():
    """選手追加処理（入力欄クリア用コールバック）"""
    new_player = st.session_state.new_player_input
    if new_player and new_player not in st.session_state.players:
        st.session_state.players.append(new_player)
    elif new_player in st.session_state.players:
        st.warning("その選手は既に登録されています。")
    # 入力欄をクリア
    st.session_state.new_player_input = ""

def calculate_win_rate(player):
    """個人の勝率を計算（最低33%保証ルール適用）"""
    # 自身の勝率を計算する際は、不戦勝(BYE)も1試合(1勝)として分母に含めます
    # （※セット型なので、戦った相手の数＋BYEの有無で総ラウンド数になります）
    matches = len(st.session_state.history[player])
    if matches == 0:
        return 0.33
    
    pts = st.session_state.standings[player]["points"]
    wr = pts / (matches * 3) # 1試合最大3ポイント計算
    
    # 33%を下回る場合は33%として扱う（TCGマイスター等の独自ルール）
    return max(wr, 0.33)

def calculate_omw(player):
    """OMW% (対戦相手の勝率の平均) を計算"""
    # ★ 不戦勝(BYE)は架空の相手なので、対戦相手のリストから除外する
    opponents = [opp for opp in st.session_state.history[player] if opp != "BYE"]
    
    if not opponents:
        return 0.0
    
    # 実際に対戦した相手の勝率（33%補正適用済み）の合計
    omw_sum = sum(calculate_win_rate(opp) for opp in opponents)
    
    # 実際に対戦した人数で割る（BYEの分は計算から完全に除外されている）
    return (omw_sum / len(opponents)) * 100

def calculate_katte_ruiten(player):
    """勝手累点 (自分が勝利した相手の累計勝ち点の合計) を計算"""
    total = 0
    # 不戦勝(BYE)は defeated(勝利した相手リスト) には入らないため、自動的に除外されます
    for opp in st.session_state.defeated[player]:
        if opp in st.session_state.standings:
            total += st.session_state.standings[opp]["points"]
    return total

def generate_swiss_pairings():
    players = st.session_state.players
    standings = st.session_state.standings
    history = st.session_state.history

    max_retries = 1000
    for _ in range(max_retries):
        available = list(players)
        bye = None

        # ①不戦勝の選定（重複防止ロジック）
        if len(available) % 2 != 0:
            # 過去に不戦勝を経験していないプレイヤーを絞り込む
            no_bye_players = [p for p in available if "BYE" not in history[p]]
            
            # 万が一全員が不戦勝経験者の場合は全体から選ぶ（小規模大会など）
            if not no_bye_players:
                no_bye_players = available
                
            min_pts = min([standings[p]["points"] for p in no_bye_players])
            min_players = [p for p in no_bye_players if standings[p]["points"] == min_pts]
            bye = random.choice(min_players)
            available.remove(bye)

        # ②勝ち点順に並べる
        pts_groups = {}
        for p in available:
            pts = standings[p]["points"]
            if pts not in pts_groups:
                pts_groups[pts] = []
            pts_groups[pts].append(p)

        sorted_available = []
        for pts in sorted(pts_groups.keys(), reverse=True):
            group = pts_groups[pts]
            random.shuffle(group)
            sorted_available.extend(group)

        # ③組み合わせ決定
        pairings = []
        valid = True
        for i in range(0, len(sorted_available), 2):
            p1 = sorted_available[i]
            p2 = sorted_available[i+1]
            if p2 in history[p1]:
                valid = False
                break
            pairings.append((p1, p2))

        if valid:
            return pairings, bye

    return None, None 

# --- UI ---
if st.session_state.phase == "setup":
    st.title("大会設定 (初期画面)")

    st.subheader("選手登録")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.text_input("選手名を入力しエンター、または登録ボタンを押す", key="new_player_input", on_change=add_player)
    with col2:
        st.write("") 
        st.button("登録", on_click=add_player)

    if st.session_state.players:
        st.write(f"登録済みの選手（計 {len(st.session_state.players)}人）: ", " / ".join(st.session_state.players))

    st.subheader("大会形式")
    formats = ["スイス式トーナメント", "トーナメント", "トーナメント+負けトーナメント", "リーグ戦(総当たり)", "リーグ戦+トーナメント"]
    selected_format = st.radio("形式を選択", formats)

    allow_draws = "なし"
    if selected_format not in ["トーナメント", "トーナメント+負けトーナメント"]:
        st.subheader("引き分けの有無")
        allow_draws = st.radio("設定", ["あり", "なし"])

    if st.button("大会スタート"):
        if len(st.session_state.players) < 2:
            st.error("選手を2名以上登録してください。")
        elif selected_format != "スイス式トーナメント":
            st.error("現在は「スイス式トーナメント」のみ実行可能です。")
        else:
            st.session_state.format = selected_format
            st.session_state.allow_draws = allow_draws
            # 成績データの初期化
            for p in st.session_state.players:
                st.session_state.standings[p] = {"points": 0, "wins": 0, "losses": 0, "draws": 0}
                st.session_state.history[p] = set()
                st.session_state.defeated[p] = set()
            st.session_state.phase = "swiss"
            st.rerun()

elif st.session_state.phase == "swiss":
    st.title(f"スイス式トーナメント (第{st.session_state.round}回戦)")

    if not st.session_state.matchups_generated:
        if st.button(f"第{st.session_state.round}回戦の組み合わせを決める"):
            pairings, bye = generate_swiss_pairings()
            if pairings is None and bye is None:
                st.error("条件を満たす組み合わせが見つかりませんでした。")
            else:
                st.session_state.current_pairings = pairings
                st.session_state.current_bye = bye
                st.session_state.matchups_generated = True
                st.rerun()
    else:
        st.subheader("対戦表")
        
        with st.form("results_form"):
            results = {}
            for idx, (p1, p2) in enumerate(st.session_state.current_pairings):
                options = [f"▽ {p1}の勝利", f"▽ {p2}の勝利"]
                if st.session_state.allow_draws == "あり":
                    options.append("▽ 引き分け")
                
                res = st.selectbox(f"{p1} vs {p2} 結果:", options, key=f"match_{idx}")
                results[(p1, p2)] = res

            if st.session_state.current_bye:
                st.info(f"不戦勝: {st.session_state.current_bye}")

            submitted = st.form_submit_button("結果を確定して次の回戦へ")
            if submitted:
                for (p1, p2), res in results.items():
                    st.session_state.history[p1].add(p2)
                    st.session_state.history[p2].add(p1)
                    
                    if "の勝利" in res:
                        winner = p1 if p1 in res else p2
                        loser = p2 if p1 in res else p1
                        st.session_state.standings[winner]["wins"] += 1
                        st.session_state.standings[winner]["points"] += 3
                        st.session_state.standings[loser]["losses"] += 1
                        
                        # 勝手累点計算のため、勝者のdefeatedリストに敗者を追加
                        st.session_state.defeated[winner].add(loser)
                        
                    elif "引き分け" in res:
                        st.session_state.standings[p1]["draws"] += 1
                        st.session_state.standings[p1]["points"] += 1
                        st.session_state.standings[p2]["draws"] += 1
                        st.session_state.standings[p2]["points"] += 1

                if st.session_state.current_bye:
                    bye_p = st.session_state.current_bye
                    st.session_state.standings[bye_p]["wins"] += 1
                    st.session_state.standings[bye_p]["points"] += 3
                    # 不戦勝は「BYE」という架空のプレイヤーとみなして履歴に追加
                    st.session_state.history[bye_p].add("BYE")

                st.session_state.round += 1
                st.session_state.matchups_generated = False
                st.rerun()

    st.markdown("---")
    st.subheader("順位表")
    
    table_data = []
    for p in st.session_state.players:
        s = st.session_state.standings[p]
        omw = calculate_omw(p)
        katte = calculate_katte_ruiten(p)
        table_data.append({
            "選手": p,
            "勝ち点": s["points"],
            "OMW%": omw,
            "勝手累点": katte,
            "勝利": s["wins"],
            "敗北": s["losses"],
            "引分": s["draws"],
        })
    
    df = pd.DataFrame(table_data)
    if not df.empty:
        # 勝ち点 -> OMW% -> 勝手累点 の優先順位でソート
        df = df.sort_values(by=["勝ち点", "OMW%", "勝手累点"], ascending=[False, False, False]).reset_index(drop=True)
        df.index = df.index + 1
        df.index.name = "順位"
        
        # OMW%の表示フォーマットを小数点第2位までの%表記に整形
        formatted_df = df.copy()
        formatted_df["OMW%"] = formatted_df["OMW%"].apply(lambda x: f"{x:.2f}%")
        
        st.dataframe(formatted_df, use_container_width=True)
