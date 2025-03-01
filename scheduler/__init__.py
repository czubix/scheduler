"""
Copyright 2023-2025 czubix

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import asyncio
import time
import re
import uuid

from datetime import datetime
from enum import Enum

from typing import Callable, Optional, Any

TIME_PATTERN = re.compile(r"\d+[smhd]")
UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}

def str_to_secs(x: str) -> int:
    return sum(int(unit[:-1]) * UNITS[unit[-1]] for unit in TIME_PATTERN.findall(x))

class TempDict(dict):
    def __init__(self, scheduler: "Scheduler", lifetime: str | int) -> None:
        self.lifetime = str_to_secs(lifetime) if isinstance(lifetime, str) else lifetime
        self.timestamps: dict[str, float] = {}

        self.schedule = scheduler.create_schedule(self.task, "1s")

    def __setitem__(self, item: Any, value: Any) -> None:
        self.timestamps[item] = time.time()
        super().__setitem__(item, value)

    def __getitem__(self, item: Any) -> Any:
        self.timestamps[item] = time.time()
        return super().__getitem__(item)

    async def task(self) -> None:
        keys = []

        for key, timestamp in self.timestamps.items():
            if time.time() - timestamp >= self.lifetime:
                keys.append(key)

        for key in keys:
            del self.timestamps[key]
            if key in self:
                del self[key]

class ScheduleFlags(Enum):
    ONCE = 1 << 0
    MULTIPLE = 1 << 1
    REPEAT = 1 << 2
    HIDDEN = 1 << 3

class Schedule:
    def __init__(self, task: Callable[..., Any], interval: int, *, name: str, args: Optional[tuple] = None, kwargs: Optional[dict] = None, times: Optional[int] = None) -> None:
        _timestamp = time.time()
        _inf = float("inf")

        self._flags = 0

        if times is None:
            self._flags |= ScheduleFlags.REPEAT.value
        elif times == 1:
            self._flags |= ScheduleFlags.ONCE.value
        elif times > 1 and times != _inf:
            self._flags |= ScheduleFlags.MULTIPLE.value

        self.task = task
        self.interval = interval
        self.timestamp = _timestamp + interval
        self.created_at = _timestamp
        self.name = name
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.times = times or _inf
        self.calls = 0

    def __str__(self) -> str:
        return f"<Schedule name={self.name!r} interval={self.interval}s flags={self.flags!r} calls=({self.calls}, {self.times})>"

    def __repr__(self) -> str:
        return f"<Schedule name={self.name!r} interval={self.interval}s flags={self.flags!r} calls=({self.calls}, {self.times})>"

    def __call__(self) -> Any:
        self.timestamp += self.interval
        self.calls += 1

        return self.task(*self.args, **self.kwargs)

    @property
    def flags(self) -> list[ScheduleFlags]:
        return [flag for flag in ScheduleFlags if flag.value & self._flags]

class Scheduler:
    def __init__(self, *, check_interval: Optional[float | int] = None, cleaner_interval: Optional[str] = None, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        check_interval = check_interval or 1

        if check_interval > 1 or check_interval <= 0:
            raise ValueError("check_interval must be between 0 and 1")

        self.loop = loop or asyncio.get_event_loop()
        self.check_interval = check_interval
        self.schedules: list[Schedule] = []
        self.finished_schedules: list[Schedule] = []
        self.canceled_schedules: list[Schedule] = []
        self._hidden_schedules: list[Schedule] = []
        self.task = self.loop.create_task(self._run())

        schedule_cleaner = self.create_schedule(self._schedule_cleaner, cleaner_interval or "1h", name="schedule_cleaner")
        self.hide_schedules(schedule_cleaner)

    def get_schedules(self, name: Optional[str] = None, *, check: Optional[Callable[..., Any]] = None) -> list[Schedule]:
        if name is None and check is None:
            return self.schedules

        schedules = []

        for schedule in self.schedules:
            if (name and schedule.name == name) or (check and check(schedule)):
                schedules.append(schedule)

        return schedules

    def create_schedule(self, task: Callable[..., Any], interval: datetime | str, **kwargs: dict) -> Schedule:
        if isinstance(interval, datetime):
            interval = (interval - datetime.now()).total_seconds()
            kwargs["times"] = 1
        elif isinstance(interval, str):
            interval = str_to_secs(interval)

        if "name" not in kwargs:
            kwargs["name"] = uuid.uuid4().hex

        if isinstance(kwargs["name"], str) is False:
            raise TypeError("name must be a string")

        schedule = Schedule(task, interval, **kwargs)
        self.schedules.append(schedule)

        return schedule

    def cancel_schedules(self, schedules: list[Schedule] | Schedule = None) -> None:
        schedules = schedules or self.schedules

        if isinstance(schedules, Schedule) is True:
            schedules = [schedules]

        for schedule in schedules:
            self.canceled_schedules.append(schedule)
            self.schedules.remove(schedule)

    def uncancel_schedules(self, schedules: list[Schedule] | Schedule = None) -> None:
        schedules = schedules or self.canceled_schedules

        if isinstance(schedules, Schedule) is True:
            schedules = [schedules]

        for schedule in schedules:
            self.schedules.append(schedule)
            self.canceled_schedules.remove(schedule)

    def hide_schedules(self, schedules: list[Schedule] | Schedule = None) -> None:
        schedules = schedules or self.schedules

        if isinstance(schedules, Schedule) is True:
            schedules = [schedules]

        for schedule in schedules:
            if schedule._flags & ScheduleFlags.HIDDEN.value == ScheduleFlags.HIDDEN.value:
                continue

            schedule._flags |= ScheduleFlags.HIDDEN.value
            self._hidden_schedules.append(schedule)
            self.schedules.remove(schedule)

    def unhide_schedules(self, schedules: list[Schedule] | Schedule = None) -> None:
        schedules = schedules or self.schedules

        if isinstance(schedules, Schedule) is True:
            schedules = [schedules]

        for schedule in schedules:
            if schedule._flags & ScheduleFlags.HIDDEN.value == 0:
                continue

            schedule._flags ^= ScheduleFlags.HIDDEN.value
            self.schedules.append(schedule)
            self._hidden_schedules.remove(schedule)

    def clear_schedules(self) -> None:
        self.schedules.clear()
        self.finished_schedules.clear()
        self.canceled_schedules.clear()

    async def _schedule_cleaner(self) -> None:
        self.finished_schedules.clear()
        self.canceled_schedules.clear()

    async def _run(self) -> None:
        while True:
            for schedule in self.schedules + self._hidden_schedules:
                if schedule.timestamp <= time.time():
                    if schedule.calls >= schedule.times:
                        if schedule._flags & ScheduleFlags.HIDDEN.value:
                            self._hidden_schedules.remove(schedule)
                            continue

                        self.finished_schedules.append(schedule)
                        self.schedules.remove(schedule)

                    self.loop.create_task(schedule())

            await asyncio.sleep(self.check_interval)