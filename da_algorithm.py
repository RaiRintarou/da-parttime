import pandas as pd
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class Operator:
    name: str
    start: int
    end: int
    home: str
    desks: List[str]
    
    def get_available_hours(self) -> List[int]:
        """オペレータが利用可能な時間帯を返す"""
        return list(range(self.start, self.end))

class DAMatchingAlgorithm:
    def __init__(self, hours: List[int], desks: List[str]):
        self.hours = hours
        self.desks = desks
        
    def _create_preferences(self, operators: List[Operator], requirements: pd.DataFrame) -> Dict[str, List[str]]:
        """各デスクのオペレータ優先順位を作成"""
        preferences = {}
        
        for desk in self.desks:
            # 各デスクで、そのデスクを対応可能なオペレータを取得
            available_ops = [op for op in operators if desk in op.desks]
            
            # 優先順位を決定（所属デスクのオペレータを優先）
            desk_ops = [op for op in available_ops if op.home == desk]
            other_ops = [op for op in available_ops if op.home != desk]
            
            # 所属デスクのオペレータを先に、その後他のデスクのオペレータを追加
            preferences[desk] = [op.name for op in desk_ops + other_ops]
            
        return preferences
    
    def _create_operator_preferences(self, operators: List[Operator]) -> Dict[str, List[str]]:
        """各オペレータのデスク優先順位を作成"""
        preferences = {}
        
        for op in operators:
            # オペレータの優先順位：所属デスクを最優先、その後対応可能なデスク
            op_prefs = [op.home] + [d for d in op.desks if d != op.home]
            preferences[op.name] = op_prefs
            
        return preferences
    
    def match(self, operators: List[Operator], requirements: pd.DataFrame) -> pd.DataFrame:
        """DAアルゴリズムによるマッチング実行"""
        # 各時間帯でDAアルゴリズムを実行
        schedule = {op.name: {f"h{h:02d}": "" for h in self.hours} for op in operators}
        
        for hour in self.hours:
            hour_col = f"h{hour:02d}"
            hour_requirements = dict(zip(requirements["desk"], requirements[hour_col]))
            
            # この時間帯で利用可能なオペレータを取得
            available_ops = [op for op in operators if op.start <= hour < op.end]
            
            if not available_ops:
                continue
                
            # この時間帯のマッチングを実行
            hour_matches = self._match_hour(available_ops, hour_requirements, hour)
            
            # 結果をスケジュールに反映
            for op_name, assigned_desk in hour_matches.items():
                schedule[op_name][hour_col] = assigned_desk
                
        return pd.DataFrame(schedule).T
    
    def _match_hour(self, operators: List[Operator], requirements: Dict[str, int], hour: int) -> Dict[str, str]:
        """特定の時間帯でのDAアルゴリズム実行"""
        # 各デスクのオペレータ優先順位を作成
        desk_preferences = self._create_preferences(operators, pd.DataFrame())
        
        # 各オペレータのデスク優先順位を作成
        op_preferences = self._create_operator_preferences(operators)
        
        # 初期化
        proposals = {op.name: 0 for op in operators}  # 各オペレータの提案回数
        desk_assignments = {desk: [] for desk in self.desks}  # 各デスクの割り当て
        matches = {op.name: "" for op in operators}  # 最終的なマッチング結果
        
        # DAアルゴリズムのメインループ
        while True:
            # まだマッチしていないオペレータを取得
            unmatched_ops = [op for op in operators if matches[op.name] == ""]
            
            if not unmatched_ops:
                break
                
            for op in unmatched_ops:
                if proposals[op.name] >= len(op_preferences[op.name]):
                    continue  # このオペレータは全てのデスクに提案済み
                    
                # 次に提案するデスクを取得
                target_desk = op_preferences[op.name][proposals[op.name]]
                
                # そのデスクの要件をチェック
                if requirements.get(target_desk, 0) > 0:
                    # デスクに空きがある場合
                    desk_assignments[target_desk].append(op.name)
                    matches[op.name] = target_desk
                    requirements[target_desk] -= 1
                else:
                    # デスクが満杯の場合、優先順位に基づいて競合を解決
                    if desk_assignments[target_desk]:
                        # 現在割り当てられているオペレータの中で最も優先度の低いものを特定
                        current_ops = desk_assignments[target_desk]
                        desk_pref = desk_preferences[target_desk]
                        
                        # 優先度の低いオペレータを見つける
                        worst_op = None
                        worst_rank = -1
                        
                        for current_op in current_ops:
                            if current_op in desk_pref:
                                rank = desk_pref.index(current_op)
                                if rank > worst_rank:
                                    worst_rank = rank
                                    worst_op = current_op
                        
                        # 新しいオペレータの優先度をチェック
                        if op.name in desk_pref and worst_op is not None:
                            new_rank = desk_pref.index(op.name)
                            if new_rank < worst_rank:
                                # 新しいオペレータの方が優先度が高い場合、置き換え
                                desk_assignments[target_desk].remove(worst_op)
                                matches[worst_op] = ""
                                desk_assignments[target_desk].append(op.name)
                                matches[op.name] = target_desk
                            else:
                                # 新しいオペレータの方が優先度が低い場合、提案を拒否
                                pass
                        else:
                            # 新しいオペレータが優先順位にない場合、提案を拒否
                            pass
                
                proposals[op.name] += 1
        
        return matches

def greedy_match(req: pd.DataFrame, ops: list):
    """従来の貪欲アルゴリズム（後方互換性のため保持）"""
    HOURS = list(range(9, 18))
    sched = {op["name"]: {f"h{h:02d}": "" for h in HOURS} for op in ops}
    for h in HOURS:
        col, need = f"h{h:02d}", dict(zip(req["desk"], req[f"h{h:02d}"]))
        for op in ops:
            if op["start"] <= h < op["end"]:
                for d in op["desks"]:
                    if need.get(d, 0) > 0 and not sched[op["name"]][col]:
                        sched[op["name"]][col], need[d] = d, need[d]-1
                        break
    return pd.DataFrame(sched).T

def da_match(req: pd.DataFrame, ops: list):
    """DAアルゴリズムによるマッチング"""
    HOURS = list(range(9, 18))
    DESKS = req["desk"].astype(str).unique().tolist()
    
    # オペレータデータをOperatorオブジェクトに変換
    operators = []
    for op_data in ops:
        op = Operator(
            name=op_data["name"],
            start=op_data["start"],
            end=op_data["end"],
            home=op_data["home"],
            desks=op_data["desks"]
        )
        operators.append(op)
    
    # DAアルゴリズムを実行
    da_algorithm = DAMatchingAlgorithm(HOURS, DESKS)
    return da_algorithm.match(operators, req) 