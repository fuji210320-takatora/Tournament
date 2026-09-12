import random
import streamlit as st

# ページ設定
st.set_page_config(page_title="スイス式トーナメント管理", layout="wide")

# セッション状態の初期化
if "players" not in st.session_state:
    st.session_state.players = []  # {"id": int, "name": str, "points": float, "opponents": list}
if "rounds" not in st.session_state:
    st.session_state.rounds = []  # 各ラウンドの対戦リスト
if "current_round" not in st.session_state:
    st.session_state.current_round = 0
if "tournament_started" not in st.session_state:
    st.session_state.tournament_started = False


def reset_tournament():
    st.session_state.players = []
    st.session_state.rounds = []
    st.session_state.current_round = 0
    st.session_state.tournament_started = False


# サイドバー：参加者管理
st.sidebar.header("参加者管理")
if not st.session_state.tournament_started:
    new_player_name = st.sidebar.text_input("参加者名")
    if st.sidebar.button("追加") and new_player_name:
        if new_player_name not in [p["name"] for p in st.session_state.players]:
            st.session_state.players.append(
                {
                    "id": len(st.session_state.players),
                    "name": new_player_name,
                    "points": 0.0,
                    "opponents": [],
                }
            )
            st.sidebar.success(f"{new_player_name} を追加しました")
        else:
            st.sidebar.warning("すでに存在する名前です")

    st.sidebar.markdown("---")
    if st.sidebar.button("トーナメント開始", type="primary"):
        if len(st.session_state.players) < 2:
            st.sidebar.error("参加者は2人以上必要です。")
        else:
            st.session_state.tournament_started = True
            st.session_state.current_round = 1
            generate_pairings()
            st.rerun()
else:
    if st.sidebar.button("トーナメントをリセット"):
        reset_tournament()
        st.rerun()

# メイン画面
st.title("🏆 スイス式トーナメント管理アプリ")

if not st.session_state.tournament_started:
    st.info(
        "左側のサイドバーから参加者を追加し、「トーナメント開始」を押してください。"
    )
    st.subheader("現在の参加者一覧")
    if st.session_state.players:
        for i, p in enumerate(st.session_state.players, 1):
            st.write(f"{i}. {p['name']}")
    else:
        st.write("まだ参加者が登録されていません。")

else:
    # 現在のラウンドを表示
    st.header(f"第 {st.session_state.current_round} ラウンド")

    # 過去の対戦と結果入力
    round_idx = st.session_state.current_round - 1
    current_matches = st.session_state.rounds[round_idx]

    st.subheader("対戦カードと結果入力")
    with st.form(f"round_{st.session_state.current_round}_form"):
        match_results = []
        for i, match in enumerate(current_matches):
            col1, col2, col3 = st.columns([3, 1, 3])
            with col1:
                st.markdown(f"**{match['player1']['name']}**")
            with col2:
                st.markdown("VS")
            with col3:
                st.markdown(f"**{match['player2']['name']}**")

            # すでに結果が決まっている場合はそれをデフォルトにする
            result_options = ["未確定", "プレイヤー1の勝ち", "引き分け", "プレイヤー2の勝ち"]
            default_index = match.get("result_index", 0)

            res = st.selectbox(
                f"試合 {i+1}: {match['player1']['name']} vs {match['player2']['name']}",
                result_options,
                index=default_index,
                key=f"match_{round_idx}_{i}",
            )
            match_results.append(res)
            st.markdown("---")

        submit_results = st.form_submit_button("ラウンド結果を確定する")

        if submit_results:
            # 結果の保存とポイントの計算
            all_decided = True
            for i, match in enumerate(current_matches):
                res = match_results[i]
                if res == "未確定":
                    all_decided = False
                    break

                match["result_index"] = result_options.index(res)

            if not all_decided:
                st.warning("すべての試合の結果を選択してください。")
            else:
                # ポイント再計算のため、全プレイヤーのポイントをリセットして再計算
                for p in st.session_state.players:
                    p["points"] = 0.0
                    p["opponents"] = []

                # これまでの全ラウンドの結果を反映
                for r_idx, r_matches in enumerate(st.session_state.rounds):
                    for m in r_matches:
                        p1 = m["player1"]
                        p2 = m["player2"]

                        # 対戦履歴に追加
                        # 参照渡し対策としてIDベースで管理するか、名前で記録
                        # ここではシンプルに相手の名前を記録
                        # (実際の実装ではIDを使う方が安全ですがシンプル化のため名前を使用)
                        if p2["name"] not in p1["opponents"]:
                            p1["opponents"].append(p2["name"])
                        if p1["name"] not in p2["opponents"]:
                            p2["opponents"].append(p1["name"])

                        res_idx = m.get("result_index", 0)
                        # プレイヤーオブジェクトを最新のセッション状態のものに更新するため検索
                        real_p1 = next(
                            p
                            for p in st.session_state.players
                            if p["id"] == p1["id"]
                        )
                        real_p2 = next(
                            p
                            for p in st.session_state.players
                            if p["id"] == p2["id"]
                        )

                        if res_idx == 1:  # P1の勝ち
                            real_p1["points"] += 1.0
                        elif res_idx == 2:  # 引き分け
                            real_p1["points"] += 0.5
                            real_p2["points"] += 0.5
                        elif res_idx == 3:  # P2の勝ち
                            real_p2["points"] += 1.0

                st.success("結果を保存しました！")

                # 次のラウンドへ進むボタンを表示するためのフラグ
                st.session_state.results_submitted = True
                st.rerun()

    # 次ラウンド生成ボタン（現在のラウンドの結果がすべて入力されている場合）
    if st.session_state.get("results_submitted", False):
        if st.button("次ラウンドのペアリングを作成する"):
            st.session_state.current_round += 1
            st.session_state.results_submitted = False
            generate_pairings()
            st.rerun()

    # スタンディング（順位表）の表示
    st.subheader("📊 現在の順位表 (スタンディング)")

    # ブッフホルツ係数（対戦相手の平均勝ち点）の計算
    standings_data = []
    for p in st.session_state.players:
        buchholz = 0.0
        for opp_name in p["opponents"]:
            opp = next(
                (item for item in st.session_state.players if item["name"] == opp_name),
                None,
            )
            if opp:
                buchholz += opp["points"]
        standings_data.append(
            {
                "名前": p["name"],
                "勝ち点": p["points"],
                "Buchholz(タイブレーク)": buchholz,
            }
        )

    # 勝ち点降順、同点ならブッフホルツ降順でソート
    standings_data.sort(
        key=lambda x: (x["勝ち点"], x["Buchholz(タイブレーク)"]), reverse=True
    )

    st.table(standings_data)


# スイス式のペアリングアルゴリズム関数
def generate_pairings():
    # プレイヤーをポイントの降順にソート
    sorted_players = sorted(
        st.session_state.players, key=lambda x: x["points"], reverse=True
    )

    paired = set()
    current_round_matches = []

    # 簡易的なスイス式ペアリング（上位から順に、まだ対戦していない近いポイントの人と組む）
    i = 0
    while i < len(sorted_players):
        p1 = sorted_players[i]
        if p1["id"] in paired:
            i += 1
            continue

        # まだペアになっておらず、かつ過去に対戦していないプレイヤーを探す
        opponent_found = False
        for j in range(i + 1, len(sorted_players)):
            p2 = sorted_players[j]
            if p2["id"] not in paired and p2["name"] not in p1["opponents"]:
                # ペア成立
                current_round_matches.append(
                    {"player1": p1, "player2": p2, "result_index": 0}
                )
                paired.add(p1["id"])
                paired.add(p2["id"])
                opponent_found = True
                break

        # もし適切な対戦相手が見つからない場合（奇数人数での不戦勝や再戦回避の妥協）
        if not opponent_found:
            for j in range(i + 1, len(sorted_players)):
                p2 = sorted_players[j]
                if p2["id"] not in paired:
                    current_round_matches.append(
                        {"player1": p1, "player2": p2, "result_index": 0}
                    )
                    paired.add(p1["id"])
                    paired.add(p2["id"])
                    opponent_found = True
                    break

        # 奇数人数で最後まで余った人の処理（不戦勝：BYE）
        if not opponent_found and p1["id"] not in paired:
            # 簡易的に不戦勝扱いにするなどの処理が必要ですが、今回はシンプルな対戦のみ
            pass

        i += 1

    st.session_state.rounds.append(current_round_matches)
