# Description:
A simple async scheduler library

# Installation:

```bash
$ git clone https://github.com/czubix/scheduler.git
$ cd scheduler
$ python3 -m pip install -U .
```

or

```bash
$ python3 -m pip install git+https://github.com/czubix/scheduler.git
```

# Example:
```py
import asyncio
from scheduler import Scheduler

scheduler = Scheduler()

async def task1():
    print("Task 1 executed.")

async def task2(arg1, arg2):
    print(f"Task 2 executed with arguments: {arg1}, {arg2}.")

scheduler.create_schedule(task1, "1s")
scheduler.create_schedule(task2, "5s", args=("arg1", "arg2"))

loop = asyncio.get_event_loop()
loop.run_forever()
```

# Documentation:
```python
class Scheduler:
    def __init__(self,
        *,
        check_interval: Optional[Union[float, int]] = None,
        schedule_cleaner_interval: Optional[str] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        ...

    def get_schedules(self,
        name: Optional[str] = None,
        *,
        check: Optional[Callable] = None
    ) -> List[Schedule]:
        ...

    def create_schedule(self,
        task: Callable,
        interval: Union[datetime, str],
        **kwargs: dict
    ) -> Schedule:
        ...

    def cancel_schedules(self,
        schedules: Union[List[Schedule], Schedule] = None
    ) -> None:
        ...

    def uncancel_schedules(self,
        schedules: Union[List[Schedule], Schedule] = None
    ) -> None:
        ...

    def hide_schedules(self,
        schedules: Union[List[Schedule], Schedule] = None
    ) -> None:
        ...

    def unhide_schedules(self,
        schedules: Union[List[Schedule], Schedule] = None
    ) -> None:
        ...

    def clear_schedules(self) -> None:
        ...
```