# Basic-logging

This tiny utility presents a handy console logging configuration having:
* Microsecond timestamp.
* Tz-aware (utc by default) datetime.
* Json (by default) serialized logs. 

The logger's time format can be any valid python datetime's one, 
by default - `%Y-%m-%d %H:%M:%S.%f%z` (i.e "2021-09-23 15:44:22.379953+0000").

🎮 Usage
---
All boils down to one function - `configure_logging`, see its docstring for documentation.  
This function only configures console which by most this is what cloud run programs or similar need 
but can be used as a based and be added more handlers (file, mail, ...) via the _extra_ or manually. 

🧪 Tests
---
From this project's directory - 
```shell
$ pytest -v --doctest-modules .
```
