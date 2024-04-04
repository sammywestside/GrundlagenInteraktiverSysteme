# GrundlagenInteraktiverSysteme

# Idee:
In meinem Projekt wird man mit imaginären Stocks traden können. Die preise werden aktuell von der Yahoo business seite sein. Die währung in Dollar. Aber is wird natürlich nur imaginäres geld verwendet.

# Seitenaufbau:
Die folgenden Seiten sind beinhaltet: Register/Login Seite, die seite auf der man sein account erstellt oder sich mit anmeldet; Quote Seite, mit diesem Link wird man mithilfe der API den aktuellen preise eines beliebigen Stocks nachschauen können; Buy Seite, auf dieser Seite werden diese Stocks dann gekauft werden können; Sell Seite, hier wird man seine gekauften stocks wieder verkaufen können; History, hie wird man seine kauf historie einsehen können; Startseite, nach der anmeldung wird man auf dieser Seite einen überblick auf seine finanzen und besitze erhalten.

# Datenbank:
Gespeichert in einer SQLite3 Datenbank werden die anmelede daten des users sowie die Transaktionen. Diese werden einmal in einer Tablle als reine Transaktion gespecihert und anderseits in einer weiteren Tabelle wird man die aktuell in besitz habenden Stocks speichern können.


Das Projetk is nicht nur html, css und javascript sonder auch python und flask im backend um die sqlite datenbank besser erreichen zu können. Mit python werden die ganzen anpassungen und einträge mit der Dataenbank gemacht. Was wann von wem gekauft oder verkauft wurde usw. Die Hauptfunktionen dabei liegen im nachschlagen der preise von gewünschten Stocks. Dazu kommt noch, dass man diese nachgeschlagenen stocks dann kaufen oder verkaufen kann. Danach wird auch ein link der seite eine kaufgeschichte anzeigen werden. Sodass der user ein komplettes paket für das stock-trading bekommt. Die anmeldung und registrierung eines eigenes accounts sorgt für ene noch weitere komponente um die seite relativ real-nah zu gestalten.
