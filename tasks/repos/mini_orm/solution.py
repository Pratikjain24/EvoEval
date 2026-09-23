"""Mini ORM: parameterized SQL query builder."""

from typing import Any, Dict, List, Tuple


class QueryBuilder:
    """Safe parameterized SQL query generator."""

    def __init__(self, table: str):
        self.table = table
        self.where_clauses: List[str] = []
        self.params: List[Any] = []

    def where(self, column: str, value: Any) -> "QueryBuilder":
        self.where_clauses.append(f"{column} = ?")
        self.params.append(value)
        return self

    def build_select(self) -> Tuple[str, List[Any]]:
        sql = f"SELECT * FROM {self.table}"
        if self.where_clauses:
            sql += " WHERE " + " AND ".join(self.where_clauses)
        return sql, list(self.params)
