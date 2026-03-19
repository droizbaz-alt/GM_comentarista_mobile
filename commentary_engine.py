import requests
import os
import chess
import chess.pgn
import chess.engine
import time
import re
import io
import lichess_api
from ai_client import AIClient
class CommentaryEngine:
    # Pre-compiled regex for technical chess tags (eval, tg, evp, clk, emt)
    TAG_RE = re.compile(r'\[%(eval|tg|evp|clk|emt).*?\]')
    # Clean non-text symbols for cleaner comparison
    CLEAN_RE = re.compile(r'[\?\!]+|\$\d+')

    def __init__(self, engine, depth=18, api_key=None, knowledge_context=None, syzygy_path=None, use_online_syzygy=False, enable_ai=True, model_name="gemini-2.0-flash", use_search=False, use_thinking=False, pro_model_name=None, lite_model_name=None, use_hybrid=False, critical_threshold=0.75, use_cache=True):
        self.engine = engine
        self.depth = depth
        self.knowledge_context = knowledge_context
        self.syzygy_path = syzygy_path
        self.use_online_syzygy = use_online_syzygy
        self.enable_ai = enable_ai
        self.model_name = model_name
        self.pro_model_name = pro_model_name
        self.lite_model_name = lite_model_name
        self.use_hybrid = use_hybrid
        self.critical_threshold = critical_threshold
        self.last_error = None
        self.tablebase = None

        # --- AI Client (centralizes all Gemini logic) ---
        self.ai = None
        if enable_ai and api_key:
            self.ai = AIClient(
                api_key=api_key,
                use_cache=use_cache,
                use_search=use_search,
                use_thinking=use_thinking,
            )
            if self.ai.last_error:
                self.last_error = self.ai.last_error

        if self.syzygy_path:
            try:
                import chess.syzygy
                self.tablebase = chess.syzygy.open_tablebase(self.syzygy_path)
            except Exception as e:
                self.last_error = f"Syzygy Error: {e}"
    def analyze_game(self, game, callback=None):
        board = game.board()
        node = game
        analysis_metadata = []
        critical_moments = []
        prev_eval = 0.0 # From White's POV 
        
        ply_count = 0
        while not node.is_end():
            if callback: callback(ply_count, board.turn, status="engine")
            next_node = node.next()
            move = next_node.move
            ply_count += 1
            
            is_capture = board.is_capture(move)
            moved_piece = board.piece_at(move.from_square)
            captured_piece = board.piece_at(move.to_square)
            is_pawn_structure_change = (
                (moved_piece and moved_piece.piece_type == chess.PAWN and is_capture) or 
                (captured_piece and captured_piece.piece_type == chess.PAWN) or            
                (move.promotion is not None) or                                             
                board.is_en_passant(move)
            )
            wdl, dtz = self._probe_syzygy(board)
            info = self.engine.analyse(board, chess.engine.Limit(depth=self.depth), multipv=3)
            best_eval = info[0]["score"]
            played_move_score = None
            rank = -1
            for i, pv in enumerate(info):
                if pv["pv"][0] == move:
                    rank = i + 1
                    played_move_score = pv["score"]
                    break
            if played_move_score is None:
                board.push(move)
                info_after = self.engine.analyse(board, chess.engine.Limit(depth=self.depth))
                played_move_score = info_after["score"]
                board.pop()
            curr_pov = played_move_score.pov(board.turn).score(mate_score=10000)
            loss = (best_eval.pov(board.turn).score(mate_score=10000) - curr_pov)
            
            if (loss > 50) or (is_capture and loss > 20):
                best_pv = info[0].get("pv")
                if best_pv and best_pv[0] != move:
                    if not any(v.move == best_pv[0] for v in node.variations):
                        self._add_pv(node, best_pv[:16], info[0]["score"])
            
            eval_tag_parts = []
            if loss > 50: eval_tag_parts.append(f"[%eval {curr_pov/100.0:+.2f}]")
            if wdl is not None:
                res_map = {1: "Win", 0: "Draw", -1: "Loss"}
                eval_tag_parts.append(f"[%tg {res_map.get(wdl, '?')}]")
            if eval_tag_parts:
                eval_tag = " ".join(eval_tag_parts)
                next_node.comment = f"{eval_tag} {next_node.comment}" if next_node.comment else eval_tag
            # --- ADVANCED STRUCTURE ANALYSIS ---
            def get_structural_flags(b, m):
                flags = []
                color = b.turn
                # Doubled pawns check
                file = chess.square_file(m.to_square)
                pawns_on_file = [s for s in b.pieces(chess.PAWN, color) if chess.square_file(s) == file]
                if len(pawns_on_file) > 1: flags.append("Dob") 
                
                # Isolated pawns check
                adj_files = []
                if file > 0: adj_files.append(file - 1)
                if file < 7: adj_files.append(file + 1)
                has_adj = False
                for f in adj_files:
                    if any(chess.square_file(s) == f for s in b.pieces(chess.PAWN, color)):
                        has_adj = True; break
                if not has_adj: flags.append("Iso")
                
                # Passed pawn check (if pawn move)
                piece = b.piece_at(m.from_square)
                if piece and piece.piece_type == chess.PAWN:
                    # Custom passed pawn detection
                    sq = m.to_square
                    file = chess.square_file(sq)
                    rank = chess.square_rank(sq)
                    opp = not color
                    is_p = True
                    for f in range(max(0, file - 1), min(8, file + 2)):
                        for r in range(rank + (1 if color else -1), 8 if color else -1, 1 if color else -1):
                            if b.piece_at(chess.square(f, r)) == chess.Piece(chess.PAWN, opp):
                                is_p = False
                                break
                        if not is_p: break
                    if is_p: flags.append("Pas")
                
                return "|".join(flags) if flags else None
            struct_flags = get_structural_flags(board, move)
            
            # Use White POV consistently for the difference calculation to avoid player-turn flip issues
            curr_eval_white = played_move_score.white().score(mate_score=10000) / 100.0
            eval_diff = abs(curr_eval_white - prev_eval)
            
            # --- REFINED CRITICAL MOMENT LOGIC ---
            # Criteria: 1. Big eval change AND (2. Side change OR 3. Advantage loss)
            
            # Side Change check (White advantage, Black advantage, or Equal)
            def get_side(v):
                if v > 1.0: return "W"
                if v < -1.0: return "B"
                return "E"
            
            side_prev = get_side(prev_eval)
            side_curr = get_side(curr_eval_white)
            side_changed = side_prev != side_curr
            
            # Advantage Loss check (e.g. from 1.5 to 0.5)
            # We check if absolute value dropped below 1.0 significantly
            adv_lost = (abs(prev_eval) >= 1.0 and abs(curr_eval_white) < 1.0)
            
            # Basic threshold check
            is_significant_change = eval_diff >= self.critical_threshold
            
            is_critical = is_significant_change and (side_changed or adv_lost)
            
            if is_critical:
                critical_moments.append(len(analysis_metadata))

            analysis_metadata.append({
                "m": board.fullmove_number, "t": "Bl" if board.turn == chess.WHITE else "Ne",
                "san": board.san(move), "eval": curr_eval_white, "loss": loss / 100.0,
                "rank": rank, "tb": (wdl, dtz) if wdl is not None else None,
                "cap": is_capture, "estrp": is_pawn_structure_change, 
                "sfl": struct_flags, "fen": board.fen()
            })
            prev_eval = curr_eval_white
            board.push(move)
            node = next_node
        
        if self.ai and self.ai.is_ready and self.enable_ai:
            original_pgn = str(game)
            ai_results = []

            # 1. Base Commentary (Lite model for the whole game)
            lite_model = self.lite_model_name or self.model_name
            if callback: callback(ply_count, board.turn, status="ai_start")
            summary_text = self._build_stockfish_summary(analysis_metadata)
            base_ai_pgn = self.ai.generate_commentary(
                pgn_text=original_pgn,
                summary=summary_text,
                knowledge_context=self.knowledge_context or "",
                is_enhancement=False,
                model_name=lite_model,
            )
            if base_ai_pgn:
                ai_results.append(base_ai_pgn)
            if self.ai.last_error:
                self.last_error = self.ai.last_error

            # 2. Critical Enhancements (Pro model for specific windows)
            if self.use_hybrid and self.pro_model_name and critical_moments:
                num_crit = len(critical_moments)
                for idx, m_idx in enumerate(critical_moments):
                    if callback:
                        callback(idx + 1, num_crit, status="ai_enhancing")

                    start_m = max(0, m_idx - 10)
                    end_m = min(len(analysis_metadata) - 1, m_idx + 2)
                    win_metadata = analysis_metadata[start_m:end_m + 1]

                    first_m = win_metadata[0]
                    window_pgn = f'[FEN "{first_m["fen"]}"]\n\n'
                    moves_list = []
                    for m in win_metadata:
                        suffix = "." if m['t'] == "Bl" else "..."
                        moves_list.append(f"{m['m']}{suffix} {m['san']}")
                    window_pgn += " ".join(moves_list)

                    win_summary = self._build_stockfish_summary(win_metadata)
                    enh_pgn = self.ai.generate_commentary(
                        pgn_text=window_pgn,
                        summary=win_summary,
                        knowledge_context=self.knowledge_context or "",
                        is_enhancement=True,
                        model_name=self.pro_model_name,
                    )
                    if enh_pgn:
                        ai_results.append(enh_pgn)

            # Sync all results back into game tree
            for res_pgn in ai_results:
                if callback: callback(ply_count, board.turn, status="syncing")
                try:
                    new_game = chess.pgn.read_game(io.StringIO(res_pgn))
                    if new_game:
                        target_node = game
                        start_fen = new_game.board().fen()
                        temp_node = game
                        while temp_node is not None:
                            if temp_node.board().fen() == start_fen:
                                target_node = temp_node
                                break
                            temp_node = temp_node.next()
                        visited: set = set()
                        self._sync_pgn_tree(target_node, new_game, callback=callback, visited=visited)
                except Exception as e:
                    self.last_error = f"Sync partial error: {e}"

            if ai_results:
                self._ensure_final_summary(game, ai_results[0])

            try:
                return str(game)
            except Exception as e:
                self.last_error = f"PGN Export Error: {e}"
                return game.accept(chess.pgn.StringExporter(columns=None, enclosures=True))
        
        # Fallback if no AI or AI failed
        self._apply_fallback_comments(game, analysis_metadata)
        try:
            return str(game)
        except:
            return game.accept(chess.pgn.StringExporter(columns=None, enclosures=True))

    def _sync_pgn_tree(self, target, source, callback=None, _depth=0, logs=None, counter=None, visited=None):
        """Recursively syncs with cycle detection and relaxed matching."""
        if visited is None: visited = set()
        
        # Use object ID to prevent recursion on same objects
        node_pair_id = (id(target), id(source))
        if node_pair_id in visited or _depth > 500:
            if _depth > 500 and logs is not None:
                logs.append(f"{'  ' * _depth}[!] Recursion limit reached at {_depth}")
            return
        visited.add(node_pair_id)

        if counter is not None:
            counter[0] += 1
            if callback and counter[0] % 50 == 0: # Increased threshold for less frequent updates
                callback(counter[0], None, status="syncing")

        if logs is not None:
            t_move = str(target.move) if target.move else "START"
            logs.append(f"{'  ' * _depth}Node: {t_move} | S_Comm: {bool(source.comment)}")

        # 1. Sync Comments
        if source.comment:
            ai_comment = self.TAG_RE.sub('', source.comment).strip()
            ai_comment_clean = self.CLEAN_RE.sub('', ai_comment).strip()
            
            if ai_comment_clean:
                if not target.comment:
                    target.comment = ai_comment
                    if logs is not None: logs.append(f"{'  ' * (_depth+1)}-> Set New Comment")
                else:
                    target_clean = self.CLEAN_RE.sub('', self.TAG_RE.sub('', target.comment)).strip()
                    # Logic: If target only had tags or if comments don't overlap, append.
                    if not target_clean or (ai_comment_clean not in target_clean and target_clean not in ai_comment_clean):
                        target.comment = f"{target.comment} {ai_comment}".strip()
                        if logs is not None: logs.append(f"{'  ' * (_depth+1)}-> Appended AI Comment")

        # 2. Relaxed Mainline Following
        s_next = source.next()
        t_next = target.next()
        
        if s_next:
            matched_mainline = False
            if t_next:
                if s_next.move == t_next.move:
                    self._sync_pgn_tree(t_next, s_next, callback=callback, _depth=_depth+1, logs=logs, counter=counter, visited=visited)
                    matched_mainline = True
                else:
                    for t_var in target.variations:
                        if t_var.move == s_next.move:
                            self._sync_pgn_tree(t_var, s_next, callback=callback, _depth=_depth+1, logs=logs, counter=counter, visited=visited)
                            matched_mainline = True
                            break
            
            if not matched_mainline:
                try:
                    move = s_next.move
                    # CRITICAL: Validate move legality before adding to tree to prevent AssertionError in str(game)
                    if target.board().is_legal(move):
                        added = target.add_variation(move)
                        self._sync_pgn_tree(added, s_next, callback=callback, _depth=_depth+1, logs=logs, counter=counter, visited=visited)
                        if logs is not None: logs.append(f"{'  ' * (_depth+1)}-> Added variation for AI Move: {move}")
                    else:
                        if logs is not None: logs.append(f"{'  ' * (_depth+1)}-> IGNORED illegal AI move: {move}")
                except Exception as e:
                    if logs is not None: logs.append(f"{'  ' * (_depth+1)}-> Failed to add AI move {s_next.move}: {e}")

        # 3. Variations Sync
        for s_var in source.variations:
            matched = False
            for t_node in target.variations:
                if t_node.move == s_var.move:
                    self._sync_pgn_tree(t_node, s_var, callback=callback, _depth=_depth+1, logs=logs, counter=counter, visited=visited)
                    matched = True
                    break
            
            if not matched and t_next and t_next.move == s_var.move:
                self._sync_pgn_tree(t_next, s_var, callback=callback, _depth=_depth+1, logs=logs, counter=counter, visited=visited)
                matched = True
            
            if not matched:
                try:
                    move = s_var.move
                    if target.board().is_legal(move):
                        added = target.add_variation(move)
                        self._sync_pgn_tree(added, s_var, callback=callback, _depth=_depth+1, logs=logs, counter=counter, visited=visited)
                        if logs is not None: logs.append(f"{'  ' * (_depth+1)}-> Added new AI variation: {move}")
                    else:
                        if logs is not None: logs.append(f"{'  ' * (_depth+1)}-> IGNORED illegal AI variation: {move}")
                except:
                    pass
    def _ensure_final_summary(self, game, ai_pgn_text):
        """Extracts the final summary block from AI PGN and ensures it is in the last node of target."""
        pattern = r'\{\s*\[MOMENTOS CRÍTICOS\].*?\}'
        match = re.search(pattern, ai_pgn_text, re.DOTALL)
        if match:
            final_comment = match.group(0).strip("{} \n")
            # Find last node in target game
            curr = game
            while not curr.is_end():
                curr = curr.next()
            
            if final_comment not in curr.comment:
                curr.comment = f"{curr.comment} {final_comment}" if curr.comment else final_comment

    def _apply_fallback_comments(self, game, metadata):
        node, idx = game, 0
        while not node.is_end():
            next_node = node.next()
            data = metadata[idx]
            comment = []
            if data["tb"] and data["tb"][0] == 0: comment.append("[Final: Tablas]")
            if data["loss"] > 3.0: comment.append(f"?? Error decisivo (Eval: {data['eval']:+0.2f})")
            elif data["loss"] > 1.5: comment.append(f"? Error importante (Eval: {data['eval']:+0.2f})")
            if comment:
                f_str = " ".join(comment)
                next_node.comment = f"{next_node.comment} {f_str}" if next_node.comment else f_str
            node, idx = next_node, idx + 1
            
    def _probe_syzygy(self, board):
        wdl = dtz = None
        if self.tablebase:
            try:
                wdl = self.tablebase.probe_wdl(board)
                dtz = self.tablebase.probe_dtz(board)
            except: pass 
        if wdl is None and self.use_online_syzygy:
            try:
                url = "https://tablebase.lichess.ovh/standard"
                res = requests.get(url, params={'fen': board.fen()}, timeout=2.0)
                if res.status_code == 200:
                    d = res.json()
                    cat = d.get("category")
                    wdl = 1 if cat == "win" else -1 if cat == "loss" else 0 if cat in ["draw", "cursed_win", "blessed_loss"] else None
                    dtz = d.get("dtz")
            except: pass
        return wdl, dtz
    def _add_pv(self, node, moves, score=None):
        current = node
        first = True
        for m in moves:
            current = current.add_variation(m)
            if first and score is not None:
                try:
                    s_val = score.white().score(mate_score=10000)
                    if s_val is not None:
                        s_str = f"{s_val/100.0:+.2f}"
                        current.comment = f"[{s_str}] {current.comment}" if current.comment else f"[{s_str}]"
                except: pass
            first = False 
    def _build_stockfish_summary(self, metadata: list) -> str:
        """Construye el bloque de datos técnicos de Stockfish para el prompt de la IA."""
        summary = "\nDATOS TÉCNICOS DE APOYO (STOCKFISH & SYZYGY):\n"
        for d in metadata:
            is_interesting = (
                abs(d['loss']) > 0.10
                or d['rank'] > 1
                or d['m'] <= 10
                or d.get('cap') or d.get('estrp')
                or d.get('sfl')
                or d['tb'] is not None
            )

            theory_info = ""
            if d['m'] <= 12: # Reducido de 25 a 12 para evitar exceso de peticiones a Lichess
                stats, _ = lichess_api.get_opening_stats(d['fen'])
                if stats and stats.get('moves'):
                    for m in stats['moves']:
                        if m['san'] == d['san']:
                            theory_info = f" | TEORÍA: {m['san']} ({m['white']+m['draws']+m['black']} part.)"
                            is_interesting = True
                            break
                    if not theory_info:
                        theory_info = " | DESVÍO TEORÍA"
                        is_interesting = True

            if is_interesting:
                tb_str = f" [TB: {d['tb']}]" if d["tb"] else ""
                cap_str = " | Cap=✓" if d.get("cap") else ""
                estrp_str = " | EstrP=✓" if d.get("estrp") else ""
                sfl_str = f" | Flags={d['sfl']}" if d.get("sfl") else ""
                summary += f"{d['m']}.{d['t']}: {d['san']} | Eval: {d['eval']:+0.2f} | Loss: {d['loss']:0.2f} | Rank: {d['rank']}{cap_str}{estrp_str}{sfl_str}{tb_str}{theory_info}\n"
            else:
                summary += f"{d['m']}.{d['t']}: {d['san']}\n"

        return summary
