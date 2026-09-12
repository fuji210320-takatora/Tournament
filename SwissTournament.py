from collections import defaultdict
import math
import random
import streamlit as st

# ページ設定
st.set_page_config(page_title="スイス式トーナメント管理", layout="wide")


# スイス式のペアリングアルゴリズム関数
def generate_pairings():
  players = st.session_state.players

  # 奇数人の場合、不戦勝（BYE）になる人を「最下位の勝点グループ」から1人選ぶ
  bye_player = None
  active_players = list(players)

  if len(active_players) % 2 != 0:
    min_points = min(p["points"] for p in active_players)
    lowest_group = [p for p in active_players if p["points"] == min_points]

    not_yet_bye = [p for p in lowest_group if p.get("bye_count", 0) == 0]
    if not_yet_bye:
      bye_player = random.choice(not_yet_bye)
    else:
      bye_player = random.choice(lowest_group)

    active_players = [p for p in active_players if p["id"] != bye_player["id"]]

  # 残りの偶数人でペアリングを行う（成績上位順、同じ勝点内はランダム）
  sorted_players = sorted(active_players, key=lambda x: x["points"], reverse=True)

  brackets = defaultdict(list)
  for p in sorted_players:
    brackets[p["points"]].append(p)

  ordered_pool = []
  unique_points = sorted(
      list(set(p["points"] for p in sorted_players)), reverse=True
  )
  for pt in unique_points:
    group = brackets[pt]
    random.shuffle(group)
    ordered_pool.extend(group)

  paired = set()
  current_round_matches = []

  i = 0
  while i < len(ordered_pool):
    p1 = ordered_pool[i]
    if p1["id"] in paired:
      i += 1
      continue

    opponent_found = False

    # 1. 同じ勝点の中で未対戦の人を探す
    for j in range(i + 1, len(ordered_pool)):
      p2 = ordered_pool[j]
      if (
          p2["id"] not in paired
          and p2["points"] == p1["points"]
          and p2["name"] not in p1["opponents"]
      ):
        current_round_matches.append(
            {"player1": p1, "player2": p2, "is_bye": False, "result_index": 0}
        )
        paired.add(p1["id"])
        paired.add(p2["id"])
        opponent_found = True
        break

    # 2. 同じ勝点にいない場合、下の勝点の未対戦の人を探す
    if not opponent_found:
      for j in range(i + 1, len(ordered_pool)):
        p2 = ordered_pool[j]
        if p2["id"] not in paired and p2["name"] not in p1["opponents"]:
          current_round_matches.append(
              {"player1": p1, "player2": p2, "is_bye": False, "result_index": 0}
          )
          paired.add(p1["id"])
          paired.add(p2["id"])
          opponent_found = True
          break

    # 3. それでも見つからない場合（再戦を許容）
    if not opponent_found:
      for j in range(i + 1, len(ordered_pool)):
        p2 = ordered_pool[j]
        if p2["id"] not in paired:
          current_round_matches.append(
              {"player1": p1, "player2": p2, "is_bye": False, "result_index": 0}
          )
          paired.add(p1["id"])
          paired.add(p2["id"])
          opponent_found = True
          break

    i += 1

  if bye_player:
    real_bye = next(p for p in st.session_state.players if p["id"] == bye_player["id"])
    real_bye["bye_count"] = real_bye.get("bye_count", 0) + 1
    current_round_matches.append(
        {"player1": real_bye, "player2": None, "is_bye": True, "result_index": 0}
    )

  st.session_state.rounds.append(current_round_matches)


# セッション状態の初期化
if "players" not in st.session_state:
  st.session_state.players = []
if "rounds" not in st.session_state:
  st.session_state.rounds = []
if "current_round" not in st.session_state:
  st.session_state.current_round = 0
if "tournament_started" not in st.session_state:
  st.session_state.tournament_started = False
if "total_rounds" not in st.session_state:
  st.session_state.total_rounds = 0
if "tournament_finished" not in st.session_state:
  st.session_state.tournament_finished = False


def reset_tournament():
  st.session_state.players = []
  st.session_state.rounds = []
  st.session_state.current_round = 0
  st.session_state.tournament_started = False
  st.session_state.total_rounds = 0
  st.session_state.tournament_finished = False


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
              "wins": 0,
              "losses": 0,
              "draws": 0,
              "bye_count": 0,
              "opponents": [],
          }
      )
      st.sidebar.success(f"{new_player_name} を追加しました")
    else:
      st.sidebar.warning("すでに存在する名前です")

  st.sidebar.markdown("---")
  if st.sidebar.button("トーナメント開始", type="primary"):
    num_players = len(st.session_state.players)
    if num_players < 2:
      st.sidebar.error("参加者は2人以上必要です。")
    else:
      st.session_state.tournament_started = True
      st.session_state.current_round = 1
      # スイス式の推奨ラウンド数（ceil(log2(N))）を自動設定
      st.session_state.total_rounds = max(1, math.ceil(math.log2(num_players)))
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
  st.header(
      f"第 {st.session_state.current_round} ラウンド / 全 {st.session_state.total_rounds} ラウンド予定"
  )

  round_idx = st.session_state.current_round - 1
  current_matches = st.session_state.rounds[round_idx]

  if not st.session_state.tournament_finished:
    st.subheader("対戦カードと結果入力")
    with st.form(f"round_{st.session_state.current_round}_form"):
      match_results = []
      result_options = ["未確定", "プレイヤー1の勝ち", "引き分け", "プレイヤー2の勝ち"]

      for i, match in enumerate(current_matches):
        if match["is_bye"]:
          st.markdown(
              f"**{match['player1']['name']}** vs 🚫 (不戦勝) —— *自動的に勝ちになります*"
          )
          match_results.append("不戦勝")
        else:
          col1, col2, col3 = st.columns([3, 1, 3])
          with col1:
            st.markdown(f"**{match['player1']['name']}**")
          with col2:
            st.markdown("VS")
          with col3:
            st.markdown(f"**{match['player2']['name']}**")

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
        all_decided = True
        for i, match in enumerate(current_matches):
          if match["is_bye"]:
            continue
          res = match_results[i]
          if res == "未確定":
            all_decided = False
            break
          match["result_index"] = result_options.index(res)

        if not all_decided:
          st.warning("すべての試合の結果を選択してください。")
        else:
          # 成績の再集計
          for p in st.session_state.players:
            p["points"] = 0.0
            p["wins"] = 0
            p["losses"] = 0
            p["draws"] = 0
            p["opponents"] = []

          for r_idx, r_matches in enumerate(st.session_state.rounds):
            for m in r_matches:
              p1 = m["player1"]
              real_p1 = next(
                  p for p in st.session_state.players if p["id"] == p1["id"]
              )

              if m["is_bye"]:
                real_p1["points"] += 1.0
                real_p1["wins"] += 1
              else:
                p2 = m["player2"]
                real_p2 = next(
                    p for p in st.session_state.players if p["id"] == p2["id"]
                )

                if p2["name"] not in real_p1["opponents"]:
                  real_p1["opponents"].append(p2["name"])
                if real_p1["name"] not in real_p2["opponents"]:
                  real_p2["opponents"].append(real_p1["name"])

                res_idx = m.get("result_index", 0)
                if res_idx == 1:
                  real_p1["points"] += 1.0
                  real_p1["wins"] += 1
                  real_p2["losses"] += 1
                elif res_idx == 2:
                  real_p1["points"] += 0.5
                  real_p2["points"] += 0.5
                  real_p1["draws"] += 1
                  real_p2["draws"] += 1
                elif res_idx == 3:
                  real_p2["points"] += 1.0
                  real_p2["wins"] += 1
                  real_p1["losses"] += 1

          st.success("結果を保存しました！")
          st.session_state.results_submitted = True
          st.rerun()

  # スタンディング（順位表）の計算・ソート
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
            "戦績": f"{p['wins']}勝 {p['losses']}敗 {p['draws']}分",
            "Buchholz(タイブレーク)": buchholz,
        }
    )

  standings_data.sort(
      key=lambda x: (x["勝ち点"], x["Buchholz(タイブレーク)"]), reverse=True
  )

  # 優勝確定判定（最終ラウンド終了時、または単独首位が確定した場合など）
  if st.session_state.get("results_submitted", False):
    # すべての予定ラウンドが終了したかチェック
    if st.session_state.current_round >= st.session_state.total_rounds:
      st.session_state.tournament_finished = True
      st.rerun()
    else:
      if st.button("次ラウンドのペアリングを作成する"):
        st.session_state.current_round += 1
        st.session_state.results_submitted = False
        generate_pairings()
        st.rerun()

  if st.session_state.tournament_finished:
    champion = standings_data[0]
    st.balloons()
    st.success(
        f"🎉 大会終了！ 優勝は **{champion['name']}** さんです！（勝点:"
        f" {champion['勝ち点']} / {champion['戦績']}）"
    )

  # スタンディングの表示
  st.subheader("📊 現在の順位表 (スタンディング)")
  st.table(standings_data)
