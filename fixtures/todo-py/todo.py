from dataclasses import dataclass


@dataclass
class Todo:
    id: int
    text: str
    done: bool = False


class TodoList:
    def __init__(self) -> None:
        self._items: list[Todo] = []
        self._next_id = 1

    def add(self, text: str) -> int:
        todo = Todo(id=self._next_id, text=text)
        self._items.append(todo)
        self._next_id += 1
        return todo.id

    def complete(self, todo_id: int) -> bool:
        for t in self._items:
            if t.id == todo_id:
                t.done = True
                return True
        return False

    def list(self) -> list[Todo]:
        return list(self._items)
