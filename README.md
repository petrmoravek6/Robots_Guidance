# Robots_Guidance

Jednoduchý vícevláknový server s komunikačním protokolem podle zadané specifikace vypracovaný v rámci předmětu Počítačové sítě během letního semestru 2021/22 bakalářského studia na Fakultě informačních technologií ČVUT.

Cílem úlohy bylo vytvořit vícevláknový server pro TCP/IP komunikaci a implementovat komunikační protokol podle dané specifikace. Pozor, implementace klientské části není součástí úlohy!

Server pro automatické řízení vzdálených robotů. Roboti se sami přihlašují k serveru a ten je navádí ke středu souřadnicového systému. Pro účely testování každý robot startuje na náhodných souřadnicích a snaží se dojít na souřadnici [0,0]. Na cílové souřadnici musí robot vyzvednout tajemství. Po cestě k cíli mohou roboti narazit na překážky, které musí obejít. Server zvládne navigovat více robotů najednou a implementuje bezchybně komunikační protokol.

Prvním argumentem serverové aplikace je port, druhým ip adresa serveru.

**Detailní specifikace jsou k dispozici v PDF souboru "readme.pdf"**
