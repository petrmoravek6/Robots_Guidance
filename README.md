## Robots_Guidance
=============

Cílem úlohy je vytvořit vícevláknový server pro TCP/IP komunikaci a implementovat komunikační protokol podle dané specifikace. Pozor, implementace klientské části není součástí úlohy!

Server pro automatické řízení vzdálených robotů. Roboti se sami přihlašují k serveru a ten je navádí ke středu souřadnicového systému. Pro účely testování každý robot startuje na náhodných souřadnicích a snaží se dojít na souřadnici [0,0]. Na cílové souřadnici musí robot vyzvednout tajemství. Po cestě k cíli mohou roboti narazit na překážky, které musí obejít. Server zvládne navigovat více robotů najednou a implementuje bezchybně komunikační protokol.

# Detailní specifikace
Komunikace mezi serverem a roboty je realizována plně textovým protokolem. Každý příkaz je zakončen dvojicí speciálních symbolů „\a\b“. (Jsou to dva znaky '\a' a '\b'.) Server musí dodržet komunikační protokol do detailu přesně, ale musí počítat s nedokonalými firmwary robotů (viz sekce Speciální situace).

Zprávy serveru:

Název	Zpráva Popis
SERVER_CONFIRMATION	<16-bitové číslo v decimální notaci>\a\b	Zpráva s potvrzovacím kódem. Může obsahovat maximálně 5 čísel a ukončovací sekvenci \a\b.
SERVER_MOVE	102 MOVE\a\b	Příkaz pro pohyb o jedno pole vpřed
SERVER_TURN_LEFT	103 TURN LEFT\a\b	Příkaz pro otočení doleva
SERVER_TURN_RIGHT	104 TURN RIGHT\a\b	Příkaz pro otočení doprava
SERVER_PICK_UP	105 GET MESSAGE\a\b	Příkaz pro vyzvednutí zprávy
SERVER_LOGOUT	106 LOGOUT\a\b	Příkaz pro ukončení spojení po úspěšném vyzvednutí zprávy
SERVER_KEY_REQUEST	107 KEY REQUEST\a\b	Žádost serveru o Key ID pro komunikaci
SERVER_OK	200 OK\a\b	Kladné potvrzení
SERVER_LOGIN_FAILED	300 LOGIN FAILED\a\b	Nezdařená autentizace
SERVER_SYNTAX_ERROR	301 SYNTAX ERROR\a\b	Chybná syntaxe zprávy
SERVER_LOGIC_ERROR	302 LOGIC ERROR\a\b	Zpráva odeslaná ve špatné situaci
SERVER_KEY_OUT_OF_RANGE_ERROR	303 KEY OUT OF RANGE\a\b	Key ID není v očekávaném rozsahu
Zprávy klienta:

Název	Zpráva	Popis	Ukázka	Maximální délka
CLIENT_USERNAME	<user name>\a\b	Zpráva s uživatelským jménem. Jméno může být libovolná sekvence znaků kromě kromě dvojice \a\b.	Umpa_Lumpa\a\b	20
CLIENT_KEY_ID	<Key ID>\a\b	Zpráva obsahující Key ID. Může obsahovat pouze celé číslo o maximálně třech cifrách.	2\a\b	5
CLIENT_CONFIRMATION	<16-bitové číslo v decimální notaci>\a\b	Zpráva s potvrzovacím kódem. Může obsahovat maximálně 5 čísel a ukončovací sekvenci \a\b.	1009\a\b	7
CLIENT_OK	OK <x> <y>\a\b	Potvrzení o provedení pohybu, kde x a y jsou souřadnice robota po provedení pohybového příkazu.	OK -3 -1\a\b	12
CLIENT_RECHARGING	RECHARGING\a\b	Robot se začal dobíjet a přestal reagovat na zprávy.		12
CLIENT_FULL_POWER	FULL POWER\a\b	Robot doplnil energii a opět příjímá příkazy.		12
CLIENT_MESSAGE	<text>\a\b	Text vyzvednutého tajného vzkazu. Může obsahovat jakékoliv znaky kromě ukončovací sekvence \a\b.	Haf!\a\b	100
Časové konstanty:

Název	Hodnota [s]	Popis
TIMEOUT	1	Server i klient očekávají od protistrany odpověď po dobu tohoto intervalu.
TIMEOUT_RECHARGING	5	Časový interval, během kterého musí robot dokončit dobíjení.
Komunikaci s roboty lze rozdělit do několika fází:

Autentizace
Server i klient oba znají pět dvojic autentizačních klíčů (nejedná se o veřejný a soukromý klíč):

Key ID	Server Key	Client Key
0	23019	32037
1	32037	29295
2	18789	13603
3	16443	29533
4	18189	21952
Každý robot začne komunikaci odesláním svého uživatelského jména (zpráva CLIENT_USERNAME). Uživatelské jméno múže být libovolná sekvence 18 znaků neobsahující sekvenci „\a\b“. V dalším kroku vyzve server klienta k odeslání Key ID (zpráva SERVER_KEY_REQUEST), což je vlastně identifikátor dvojice klíčů, které chce použít pro autentizaci. Klient odpoví zprávou CLIENT_KEY_ID, ve které odešle Key ID. Po té server zná správnou dvojici klíčů, takže může spočítat "hash" kód z uživatelského jména podle následujícího vzorce:

Uživatelské jméno: Mnau!

ASCII reprezentace: 77 110 97 117 33

Výsledný hash: ((77 + 110 + 97 + 117 + 33) * 1000) % 65536 = 40784
Výsledný hash je 16-bitové číslo v decimální podobě. Server poté k hashi přičte klíč serveru tak, že pokud dojde k překročení kapacity 16-bitů, hodnota jednoduše přetečení:

(40784 + 54621) % 65536 = 29869
Výsledný potvrzovací kód serveru se jako text pošle klientovi ve zprávě SERVER_CONFIRM. Klient z obdrženého kódu vypočítá zpátky hash a porovná ho s očekávaným hashem, který si sám spočítal z uživatelského jména. Pokud se shodují, vytvoří potvrzovací kód klienta. Výpočet potvrzovacího kódu klienta je obdobný jako u serveru, jen se použije klíč klienta:

(40784 + 45328) % 65536 = 20576
Potvrzovací kód klienta se odešle serveru ve zpráve CLIENT_CONFIRMATION, který z něj vypočítá zpátky hash a porovná jej s původním hashem uživatelského jména. Pokud se obě hodnoty shodují, odešle zprávu SERVER_OK, v opačném prípadě reaguje zprávou SERVER_LOGIN_FAILED a ukončí spojení. Celá sekvence je na následujícím obrázku:

Klient                  Server
​------------------------------------------
CLIENT_USERNAME     --->
                    <---    SERVER_KEY_REQUEST
CLIENT_KEY_ID       --->
                    <---    SERVER_CONFIRMATION
CLIENT_CONFIRMATION --->
                    <---    SERVER_OK
                              nebo
                            SERVER_LOGIN_FAILED
                      .
                      .
                      .
Server dopředu nezná uživatelská jména. Roboti si proto mohou zvolit jakékoliv jméno, ale musí znát sadu klíčů klienta i serveru. Dvojice klíčů zajistí oboustranou autentizaci a zároveň zabrání, aby byl autentizační proces kompromitován prostým odposlechem komunikace.

Pohyb robota k cíli
Robot se může pohybovat pouze rovně (SERVER_MOVE) a je schopen provést otočení na místě doprava (SERVER_TURN_RIGHT) i doleva (SERVER_TURN_LEFT). Po každém příkazu k pohybu odešle potvrzení (CLIENT_OK), jehož součástí je i aktuální souřadnice. Pozice robota není serveru na začátku komunikace známa. Server musí zjistit polohu robota (pozici a směr) pouze z jeho odpovědí. Z důvodů prevence proti nekonečnému bloudění robota v prostoru, má každý robot omezený počet pohybů (pouze posunutí vpřed). Počet pohybů by měl být dostatečný pro rozumný přesun robota k cíli. Následuje ukázka komunkace. Server nejdříve pohne dvakrát robotem kupředu, aby detekoval jeho aktuální stav a po té jej navádí směrem k cílové souřadnici [0,0].

Klient                  Server
​------------------------------------------
                  .
                  .
                  .
                <---    SERVER_MOVE
                          nebo
                        SERVER_TURN_LEFT
                          nebo
                        SERVER_TURN_RIGHT
CLIENT_OK       --->
                <---    SERVER_MOVE
                          nebo
                        SERVER_TURN_LEFT
                          nebo
                        SERVER_TURN_RIGHT
CLIENT_OK       --->
                <---    SERVER_MOVE
                          nebo
                        SERVER_TURN_LEFT
                          nebo
                        SERVER_TURN_RIGHT
                  .
                  .
                  .
Těsně po autentizaci robot očekává alespoň jeden pohybový příkaz - SERVER_MOVE, SERVER_TURN_LEFT nebo SERVER_TURN_RIGHT! Nelze rovnou zkoušet vyzvednout tajemství. Po cestě k cíli se nachází mnoho překážek, které musí roboti překonat objížďkou. Pro překážky platí následující pravidla:

Překážka okupuje vždy jedinou souřadnici.
Je zaručeno, že každá překážka má prázdné všechny sousední souřadnice (tedy vždy lze jednoduše objet).
Je zaručeno, že překážka nikdy neokupuje souřadnici [0,0].
Pokud robot narazí do překážky více než dvacetkrát, poškodí se a ukončí spojení.
Překážka je detekována tak, že robot dostane pokyn pro pohyb vpřed (SERVER_MOVE), ale nedojde ke změně souřadnic (zpráva CLIENT_OK obsahuje stejné souřadnice jako v předchozím kroku). Pokud se pohyb neprovede, nedojde k odečtení z počtu zbývajících kroků robota.

Vyzvednutí tajného vzkazu
Poté, co robot dosáhne cílové souřadnice [0,0], tak se pokusí vyzvednout tajný vzkaz (zpráva SERVER_PICK_UP). Pokud je robot požádán o vyzvednutí vzkazu a nenachází se na cílové souřadnici, spustí se autodestrukce robota a komunikace se serverem je přerušena. Při pokusu o vyzvednutí na cílově souřadnici reaguje robot zprávou CLIENT_MESSAGE. Server musí na tuto zprávu zareagovat zprávou SERVER_LOGOUT. (Je zaručeno, že tajný vzkaz se nikdy neshoduje se zprávou CLIENT_RECHARGING, pokud je tato zpráva serverem obdržena po žádosti o vyzvednutí jedná se vždy o dobíjení.) Poté klient i server ukončí spojení. Ukázka komunikace s vyzvednutím vzkazu:

Klient                  Server
​------------------------------------------
                  .
                  .
                  .
                <---    SERVER_PICK_UP
CLIENT_MESSAGE  --->
                <---    SERVER_LOGOUT
