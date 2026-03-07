# PodPutignano.py  v2
# Script unico che assembla il podcast "Buongiorno Putignano".
# Incorpora: MeteoNews, FarmacieNews, ItaliaNews, PutignanoNews, CuriositàNews, Putignano
# Dati incorporati: Onomastici (366), Curiosità (100) — nessun file esterno richiesto
#
# Uso:  python PodPutignano.py
# Output: Lettura.txt  →  poi lancia Podcast.py x v  →  Lettura.mp3

import re, html, time, os, sys, random, platform, subprocess
from datetime import datetime, timedelta, timezone, date
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, wait
from collections import Counter

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ============================================================
# CONFIG GLOBALE
# ============================================================

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
POD_DIR      = os.path.join(SCRIPT_DIR, "pod")
HTTP_TIMEOUT = 12
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9",
}

GIORNI_ITA = {0:"lunedì",1:"martedì",2:"mercoledì",3:"giovedì",4:"venerdì",5:"sabato",6:"domenica"}
MESI_ITA   = {1:"gennaio",2:"febbraio",3:"marzo",4:"aprile",5:"maggio",6:"giugno",
              7:"luglio",8:"agosto",9:"settembre",10:"ottobre",11:"novembre",12:"dicembre"}

# --- DATI INCORPORATI ---

ONOMASTICI_DB = {
    "01/01": "Maria Santissima Madre di Dio",
    "02/01": "San Basilio e San Gregorio",
    "03/01": "Santa Genoveffa",
    "04/01": "Sant'Ermete",
    "05/01": "Sant'Amelia",
    "06/01": "Epifania (Gaspare - Melchiorre - Baldassarre)",
    "07/01": "San Raimondo",
    "08/01": "San Massimo",
    "09/01": "San Giuliano",
    "10/01": "Sant'Aldo",
    "11/01": "Sant'Igino",
    "12/01": "San Modesto",
    "13/01": "Sant'Ilario",
    "14/01": "San Felice",
    "15/01": "San Mauro",
    "16/01": "San Marcello",
    "17/01": "Sant'Antonio Abate",
    "18/01": "Santa Margherita",
    "19/01": "San Mario",
    "20/01": "San Sebastiano",
    "21/01": "Sant'Agnese",
    "22/01": "San Vincenzo",
    "23/01": "Sant'Emerenziana",
    "24/01": "San Francesco di Sales",
    "25/01": "Conversione di San Paolo",
    "26/01": "Santi Tito e Timoteo",
    "27/01": "Sant'Angela Merici",
    "28/01": "San Tommaso d'Aquino",
    "29/01": "San Costanzo",
    "30/01": "Santa Martina",
    "31/01": "San Giovanni Bosco",
    "01/02": "Santa Verdiana",
    "02/02": "Presentazione del Signore",
    "03/02": "San Biagio",
    "04/02": "San Gilberto",
    "05/02": "Sant'Agata",
    "06/02": "San Paolo Miki",
    "07/02": "San Teodoro",
    "08/02": "San Girolamo Emiliani",
    "09/02": "Sant'Apollonia",
    "10/02": "Santa Scolastica",
    "11/02": "Beata Vergine di Lourdes",
    "12/02": "Sant'Eulalia",
    "13/02": "Santa Maura",
    "14/02": "San Valentino",
    "15/02": "San Faustino",
    "16/02": "Santa Giuliana",
    "17/02": "San Donato",
    "18/02": "San Simone",
    "19/02": "San Mansueto",
    "20/02": "San Silvano",
    "21/02": "San Pier Damiani",
    "22/02": "Santa Margherita da Cortona",
    "23/02": "San Policarpo",
    "24/02": "San Mattia",
    "25/02": "San Cesario",
    "26/02": "San Romeo",
    "27/02": "San Leandro",
    "28/02": "San Romano",
    "29/02": "San Giusto",
    "01/03": "Sant'Albino",
    "02/03": "San Basileo",
    "03/03": "Santa Cunegonda",
    "04/03": "San Casimiro",
    "05/03": "Sant'Adriano",
    "06/03": "San Giordano",
    "07/03": "Sante Perpetua e Felicita",
    "08/03": "San Giovanni di Dio",
    "09/03": "Santa Francesca Romana",
    "10/03": "San Simplicio",
    "11/03": "San Costantino",
    "12/03": "San Massimiliano",
    "13/03": "Sant'Arrigo",
    "14/03": "Santa Matilde",
    "15/03": "Santa Luisa",
    "16/03": "Sant'Eriberto",
    "17/03": "San Patrizio",
    "18/03": "San Cirillo di Gerusalemme",
    "19/03": "San Giuseppe",
    "20/03": "Santa Alessandra",
    "21/03": "San Benedetto",
    "22/03": "Santa Lea",
    "23/03": "San Turibio de Mogrovejo",
    "24/03": "San Romolo",
    "25/03": "Annunciazione (Annunziata)",
    "26/03": "Sant'Emanuele",
    "27/03": "Sant'Augusto",
    "28/03": "San Sisto",
    "29/03": "San Secondo",
    "30/03": "Sant'Amedeo",
    "31/03": "San Beniamino",
    "01/04": "Sant'Ugo",
    "02/04": "San Francesco di Paola",
    "03/04": "San Riccardo",
    "04/04": "Sant'Isidoro",
    "05/04": "San Vincenzo Ferreri",
    "06/04": "San Pietro da Verona",
    "07/04": "San Giovanni Battista de la Salle",
    "08/04": "Sant'Alberto",
    "09/04": "Santa Maria di Cleofa",
    "10/04": "San Terenzio",
    "11/04": "San Stanislao",
    "12/04": "San Giulio",
    "13/04": "San Martino",
    "14/04": "Sant'Abbondio",
    "15/04": "Sant'Annibale",
    "16/04": "Santa Bernadette",
    "17/04": "San Roberto",
    "18/04": "San Galdino",
    "19/04": "Sant'Ermogene",
    "20/04": "Sant'Adalgisa",
    "21/04": "Sant'Anselmo",
    "22/04": "San Caio",
    "23/04": "San Giorgio",
    "24/04": "San Fedele",
    "25/04": "San Marco",
    "26/04": "San Marcellino",
    "27/04": "Santa Zita",
    "28/04": "Santa Valeria",
    "29/04": "Santa Caterina da Siena",
    "30/04": "San Pio V",
    "01/05": "San Giuseppe Lavoratore",
    "02/05": "Sant'Atanasio",
    "03/05": "Santi Filippo e Giacomo",
    "04/05": "San Silvano",
    "05/05": "San Pellegrino",
    "06/05": "Santa Giuditta",
    "07/05": "Santa Flavia",
    "08/05": "San Vittore",
    "09/05": "San Gregorio",
    "10/05": "Sant'Antonino",
    "11/05": "San Fabio",
    "12/05": "Santa Rossana",
    "13/05": "Sant'Emma",
    "14/05": "San Mattia apostolo (o San Corrado)",
    "15/05": "San Torquato",
    "16/05": "Sant'Ubaldo",
    "17/05": "San Pasquale Baylon",
    "18/05": "San Venanzio",
    "19/05": "San Pietro di Morrone (Celestino V)",
    "20/05": "San Bernardino da Siena",
    "21/05": "San Vittorio",
    "22/05": "Santa Rita da Cascia",
    "23/05": "San Desiderio",
    "24/05": "Beata Vergine Maria Ausiliatrice",
    "25/05": "San Beda",
    "26/05": "San Filippo Neri",
    "27/05": "Sant'Agostino di Canterbury",
    "28/05": "Sant'Emilio",
    "29/05": "San Massimo",
    "30/05": "San Felice",
    "31/05": "Visitazione della Beata Vergine Maria",
    "01/06": "San Giustino",
    "02/06": "Sant'Erasmo",
    "03/06": "San Carlo Lwanga",
    "04/06": "San Quirino",
    "05/06": "San Bonifacio",
    "06/06": "San Norberto",
    "07/06": "San Roberto",
    "08/06": "San Medardo",
    "09/06": "Sant'Efrem",
    "10/06": "Santa Diana",
    "11/06": "San Barnaba apostolo",
    "12/06": "San Guido",
    "13/06": "Sant'Antonio da Padova",
    "14/06": "Sant'Eliseo",
    "15/06": "San Vito",
    "16/06": "Sant'Aureliano",
    "17/06": "San Gregorio",
    "18/06": "Santa Marina",
    "19/06": "Santi Gervasio e Protasio",
    "20/06": "San Silverio",
    "21/06": "San Luigi Gonzaga",
    "22/06": "San Paolino di Nola",
    "23/06": "San Lanfranco",
    "24/06": "Natività di San Giovanni Battista",
    "25/06": "San Guglielmo",
    "26/06": "San Vigilio",
    "27/06": "San Cirillo d'Alessandria",
    "28/06": "Sant'Ireneo",
    "29/06": "Santi Pietro e Paolo",
    "30/06": "Santi Primi Martiri della Chiesa Romana",
    "01/07": "San Teobaldo",
    "02/07": "Sant'Ottone",
    "03/07": "San Tommaso apostolo",
    "04/07": "Santa Elisabetta di Portogallo",
    "05/07": "Sant'Antonio Maria Zaccaria",
    "06/07": "Santa Maria Goretti",
    "07/07": "San Claudio",
    "08/07": "Sant'Adriano",
    "09/07": "Santa Letizia",
    "10/07": "Santa Rufina",
    "11/07": "San Benedetto da Norcia",
    "12/07": "San Fortunato",
    "13/07": "Sant'Enrico",
    "14/07": "San Camillo de Lellis",
    "15/07": "San Bonaventura",
    "16/07": "Beata Vergine Maria del Monte Carmelo",
    "17/07": "Sant'Alessio",
    "18/07": "San Federico",
    "19/07": "Santa Giusta",
    "20/07": "Sant'Elia",
    "21/07": "San Lorenzo da Brindisi",
    "22/07": "Santa Maria Maddalena",
    "23/07": "Santa Brigida",
    "24/07": "Santa Cristina",
    "25/07": "San Giacomo apostolo",
    "26/07": "Santi Gioacchino e Anna",
    "27/07": "Santa Liliana",
    "28/07": "San Nazario",
    "29/07": "Santa Marta",
    "30/07": "San Pietro Crisologo",
    "31/07": "Sant'Ignazio di Loyola",
    "01/08": "Sant'Alfonso Maria de' Liguori",
    "02/08": "Sant'Eusebio di Vercelli",
    "03/08": "Santa Lidia",
    "04/08": "San Giovanni Maria Vianney",
    "05/08": "Sant'Osvaldo",
    "06/08": "Trasfigurazione del Signore",
    "07/08": "San Gaetano da Thiene",
    "08/08": "San Domenico di Guzmán",
    "09/08": "Santa Teresa Benedetta della Croce",
    "10/08": "San Lorenzo",
    "11/08": "Santa Chiara",
    "12/08": "Sant'Ercolano",
    "13/08": "San Ponziano",
    "14/08": "San Massimiliano Kolbe",
    "15/08": "Assunzione di Maria (Assunta)",
    "16/08": "San Rocco",
    "17/08": "San Giacinto",
    "18/08": "Sant'Elena",
    "19/08": "San Ludovico",
    "20/08": "San Bernardo",
    "21/08": "San Pio X",
    "22/08": "Beata Vergine Maria Regina",
    "23/08": "Santa Rosa da Lima",
    "24/08": "San Bartolomeo apostolo",
    "25/08": "San Ludovico (Luigi IX)",
    "26/08": "Sant'Alessandro",
    "27/08": "Santa Monica",
    "28/08": "Sant'Agostino",
    "29/08": "Martirio di San Giovanni Battista",
    "30/08": "Santa Faustina",
    "31/08": "Sant'Aristide",
    "01/09": "Sant'Egidio",
    "02/09": "Sant'Elpidio",
    "03/09": "San Gregorio Magno",
    "04/09": "Santa Rosalia",
    "05/09": "San Vittorino",
    "06/09": "Sant'Umberto",
    "07/09": "Santa Regina",
    "08/09": "Natività della Beata Vergine Maria",
    "09/09": "San Sergio",
    "10/09": "San Nicola da Tolentino",
    "11/09": "San Diomede",
    "12/09": "Santissimo Nome di Maria",
    "13/09": "San Giovanni Crisostomo",
    "14/09": "Esaltazione della Santa Croce",
    "15/09": "Beata Vergine Maria Addolorata",
    "16/09": "Santi Cornelio e Cipriano",
    "17/09": "San Roberto Bellarmino",
    "18/09": "Santa Sofia",
    "19/09": "San Gennaro",
    "20/09": "Sant'Eustachio",
    "21/09": "San Matteo apostolo",
    "22/09": "San Maurizio",
    "23/09": "San Pio da Pietrelcina",
    "24/09": "San Pacifico",
    "25/09": "Sant'Aurelia",
    "26/09": "Santi Cosma e Damiano",
    "27/09": "San Vincenzo de' Paoli",
    "28/09": "San Venceslao",
    "29/09": "Santi Arcangeli Michele Gabriele e Raffaele",
    "30/09": "San Girolamo",
    "01/10": "Santa Teresa di Gesù Bambino",
    "02/10": "Santi Angeli Custodi (Angelo - Angela)",
    "03/10": "San Gerardo",
    "04/10": "San Francesco d'Assisi",
    "05/10": "San Placido",
    "06/10": "San Bruno",
    "07/10": "Beata Vergine Maria del Rosario",
    "08/10": "Santa Pelagia",
    "09/10": "San Dionigi",
    "10/10": "San Daniele",
    "11/10": "San Firmino",
    "12/10": "San Serafino",
    "13/10": "Sant'Edoardo",
    "14/10": "San Callisto",
    "15/10": "Santa Teresa d'Avila",
    "16/10": "Santa Margherita Maria Alacoque",
    "17/10": "Sant'Ignazio di Antiochia",
    "18/10": "San Luca evangelista",
    "19/10": "Sant'Isacco",
    "20/10": "Sant'Irene",
    "21/10": "Sant'Orsola",
    "22/10": "San Donato",
    "23/10": "San Giovanni da Capestrano",
    "24/10": "Sant'Antonio Maria Claret",
    "25/10": "San Crispino",
    "26/10": "Sant'Evaristo",
    "27/10": "San Fiorenzo",
    "28/10": "Santi Simone e Giuda",
    "29/10": "Sant'Ermelinda",
    "30/10": "San Germano",
    "31/10": "Santa Lucilla",
    "01/11": "Tutti i Santi",
    "02/11": "Commemorazione dei Defunti",
    "03/11": "Santa Silvia",
    "04/11": "San Carlo Borromeo",
    "05/11": "San Zaccaria",
    "06/11": "San Leonardo",
    "07/11": "Sant'Ernesto",
    "08/11": "San Goffredo",
    "09/11": "Sant'Oreste",
    "10/11": "San Leone Magno",
    "11/11": "San Martino di Tours",
    "12/11": "San Giosafat",
    "13/11": "San Diego",
    "14/11": "San Giocondo",
    "15/11": "Sant'Alberto Magno",
    "16/11": "Santa Margherita di Scozia",
    "17/11": "Santa Elisabetta d'Ungheria",
    "18/11": "Sant'Oddone",
    "19/11": "San Fausto",
    "20/11": "Sant'Ottavio",
    "21/11": "Presentazione della Beata Vergine Maria",
    "22/11": "Santa Cecilia",
    "23/11": "San Clemente",
    "24/11": "Santa Flora",
    "25/11": "Santa Caterina d'Alessandria",
    "26/11": "San Corrado",
    "27/11": "San Virgilio",
    "28/11": "San Giacomo della Marca",
    "29/11": "San Saturnino",
    "30/11": "Sant'Andrea apostolo",
    "01/12": "Sant'Eligio",
    "02/12": "Santa Bibiana",
    "03/12": "San Francesco Saverio",
    "04/12": "Santa Barbara",
    "05/12": "San Giulio",
    "06/12": "San Nicola di Bari",
    "07/12": "Sant'Ambrogio",
    "08/12": "Immacolata Concezione (Concetta)",
    "09/12": "San Siro",
    "10/12": "Beata Vergine Maria di Loreto",
    "11/12": "San Damaso",
    "12/12": "Santa Giovanna Francesca de Chantal",
    "13/12": "Santa Lucia",
    "14/12": "San Giovanni della Croce",
    "15/12": "San Valeriano",
    "16/12": "Sant'Adelaide",
    "17/12": "San Lazzaro",
    "18/12": "San Graziano",
    "19/12": "San Dario",
    "20/12": "San Liberato",
    "21/12": "San Pietro Canisio",
    "22/12": "Santa Francesca Saverio Cabrini",
    "23/12": "San Giovanni da Kety",
    "24/12": "Sant'Adele",
    "25/12": "Natività del Signore (Natale)",
    "26/12": "Santo Stefano",
    "27/12": "San Giovanni apostolo ed evangelista",
    "28/12": "Santi Innocenti Martiri",
    "29/12": "San Tommaso Becket",
    "30/12": "Sant'Eugenio",
    "31/12": "San Silvestro",
}

CURIOSITA_DB = [
    "Oggi vi portiamo in Puglia per parlarvi di un vero e proprio record storico. Sapevate che il Carnevale di Putignano, in provincia di Bari, è considerato il più antico d'Europa? Le sue origini ufficiali vengono fatte risalire addirittura all'anno 1394. Oltre seicento anni di storia, arte e goliardia che continuano a vivere per le strade di questa splendida cittadina pugliese.",
    "Se pensate che il Carnevale duri solo un paio di settimane a febbraio, a Putignano vi faranno cambiare idea. Quello putignanese è uno dei carnevali più lunghi del mondo. I festeggiamenti, infatti, iniziano ufficialmente subito dopo Natale, precisamente il 26 dicembre, e si concludono solo il giorno del Martedì Grasso, regalando alla città mesi di satira, maschere e tradizioni.",
    "Tutto ha inizio il 26 dicembre. A Putignano il Carnevale si apre con la storica 'Festa delle Propaggini'. Questa tradizione secolare ricorda un evento sacro: la traslazione delle reliquie di Santo Stefano, portate in città per proteggerle dalle incursioni dei pirati. Da quel momento solenne nacque una festa contadina che ancora oggi segna l'inizio del periodo più pazzo dell'anno.",
    "Cosa succede a Putignano il giorno di Santo Stefano? Va in scena la 'Festa delle Propaggini'. Attori dilettanti e poeti dialettali salgono sul palco vestiti con abiti tradizionali contadini, tenendo in mano un tralcio di vite, la cosiddetta 'propaggine'. Da quel palco recitano versi satirici in rima, unendo la saggezza popolare alla presa in giro dei potenti.",
    "Nessuno è al sicuro durante le 'Propaggini' di Putignano. In questa festa del 26 dicembre che apre il Carnevale, i poeti dialettali recitano versi pungenti che prendono di mira esclusivamente i politici, gli amministratori e le personalità locali di spicco. È un momento di pura catarsi collettiva, dove il popolo, per un giorno, ha il diritto di sbeffeggiare chi comanda.",
    "Il lungo Carnevale di Putignano non si vive solo nei fine settimana. Il periodo di festa è scandito da sette giovedì, ognuno dedicato a una specifica categoria sociale che viene bonariamente presa in giro. Una vera e propria marcia di avvicinamento al Martedì Grasso che coinvolge tutta la comunità in un rituale collettivo e divertente.",
    "Sette giovedì per sette categorie da sbeffeggiare. A Putignano, le settimane prima del Martedì Grasso seguono un ordine preciso: si comincia prendendo in giro i Monsignori, poi i Preti, le Monache, i Vedovi, i Pazzi, le Donne sposate e, gran finale, i Cornuti. Un'antica tradizione che ribalta i ruoli sociali a colpi di ironia.",
    "A Putignano esiste un'istituzione decisamente insolita: l'Accademia delle Corna. Questo gruppo goliardico è l'anima del penultimo giovedì di Carnevale, dedicato agli uomini sposati. La mattina si inizia con il rito dell'ammasso delle corna in piazza, un momento di pura comicità che prepara la città al grande e goliardico taglio serale.",
    "Essere eletti 'Gran Cornuto dell'anno' a Putignano non è un'offesa, ma un onore goliardico! Durante il Giovedì dei Cornuti, l'Accademia locale seleziona un personaggio pubblico, un politico o un cittadino illustre a cui conferire questo titolo satirico. Un modo per esorcizzare la gelosia e ridere delle debolezze umane.",
    "La sera del Giovedì dei Cornuti, a Putignano, va in scena un rituale esilarante: il 'taglio delle corna'. I membri dell'Accademia, muniti di enormi cesoie, procedono al taglio simbolico delle corna del prescelto dell'anno. È una cerimonia teatrale e liberatoria che attira centinaia di curiosi nel centro storico della città.",
    "Ogni bella festa ha una fine, e a Putignano il Carnevale muore... letteralmente. La sera del Martedì Grasso si celebra un vero e proprio rito funebre per la fine dei festeggiamenti. Cittadini travestiti da preti e vedove inconsolabili piangono la scomparsa del Carnevale, celebrando la fine dell'abbondanza prima del rigore della Quaresima.",
    "Chi è il defunto che viene pianto la sera del Martedì Grasso a Putignano? Il Carnevale morente è tradizionalmente rappresentato da un grande maiale di cartapesta. Questo animale, simbolo storico di grasso e abbondanza culinaria, viene portato in processione per le vie del paese e infine bruciato, segnando la purificazione in vista della Quaresima.",
    "L'ultimo respiro del Carnevale di Putignano ha il suono di una campana gigante. La 'Campana dei Maccheroni' è un'enorme opera di cartapesta che viene posizionata nella piazza principale la sera del Martedì Grasso. Quando inizia a suonare, segna gli ultimi momenti di festa prima che scocchi la mezzanotte e inizi il digiuno quaresimale.",
    "Immaginate una piazza gremita, una gigantesca campana di cartapesta e un conto alla rovescia fatto di rintocchi. La sera del Martedì Grasso a Putignano, la Campana dei Maccheroni suona esattamente 365 volte. Ogni rintocco rappresenta un giorno dell'anno, un lungo addio alla carne e ai festeggiamenti sfrenati.",
    "Perché si chiama 'Campana dei Maccheroni'? A Putignano, i rintocchi di questa campana di cartapesta, l'ultima sera di Carnevale, segnano le ultime ore in cui è concesso mangiare carne. La tradizione vuole che i cittadini festeggino in piazza mangiando maccheroni al sugo di carne, l'ultimo pasto ricco prima del periodo di rinunce della Quaresima.",
    "I carri allegorici di Putignano non sono solo carri, sono capolavori riconosciuti a livello mondiale. Questa cittadina vanta un'eccellenza assoluta nella lavorazione della cartapesta. I maestri artigiani locali si tramandano di generazione in generazione segreti e tecniche per modellare la carta di giornale, trasformandola in sculture gigantesche e spettacolari.",
    "Come fa un pupazzo alto come un palazzo di tre piani a muoversi agilmente? Il segreto dei maestri cartapestai di Putignano sta in una tecnica di lavorazione unica. Utilizzando argilla, gesso, calchi e fogli di carta bagnata nella colla, riescono a creare figure colossali che sono, allo stesso tempo, incredibilmente leggere e resistenti alle intemperie.",
    "Quando sfilano per le strade di Putignano, tolgono il fiato. I carri allegorici di questo storico carnevale sono dei veri e propri giganti in movimento, capaci di superare i 15 metri di altezza. Altezze vertiginose che sfidano la gravità, rendendo ogni sfilata uno spettacolo ingegneristico oltre che artistico.",
    "Gestire il carnevale più antico d'Europa non è un gioco da ragazzi. A coordinare questa immensa macchina organizzativa c'è la 'Fondazione Carnevale di Putignano'. Un ente dedicato che lavora tutto l'anno per garantire che la magia della cartapesta, gli eventi collaterali e le sfilate si svolgano in totale sicurezza e splendore.",
    "Dove nascono i giganti del Carnevale di Putignano? Le enormi opere in cartapesta prendono vita in giganteschi capannoni situati alla periferia del paese. Veri e propri hangar dove, per mesi, squadre di artigiani, saldatori e pittori lavorano giorno e notte, tra impalcature e profumo di colla, per preparare i carri per le sfilate.",
    "Un tempo, i carri di Putignano venivano mossi a forza di braccia e leve. Oggi, la magia della cartapesta incontra l'alta tecnologia. I movimenti dei pupazzi sono gestiti da complessi sistemi idraulici ed elettromeccanici. Sotto i colori e la carta, batte un cuore tecnologico che permette ai giganti di muovere occhi, braccia e sorridere al pubblico.",
    "Chi l'ha detto che il Carnevale si festeggia solo d'inverno? A Putignano, dal 2006, si è deciso di raddoppiare la magia introducendo un'edizione estiva. Un'occasione fantastica per mostrare le colossali opere d'arte in cartapesta ai tantissimi turisti che affollano la Puglia nei mesi caldi, sotto un cielo stellato anziché sotto la pioggia invernale.",
    "Oggi li compriamo in sacchetti di plastica nei supermercati, ma un tempo a Putignano i coriandoli erano una faccenda seria. La loro produzione artigianale era una vera e propria micro-industria che coinvolgeva molte famiglie del paese. Venivano ricavati dagli scarti delle tipografie e delle sartorie, creando un'economia circolare ante litteram per colorare le feste.",
    "Ogni grande Carnevale ha la sua maschera simbolo, e Putignano ha 'Farinella'. Ma attenzione, non stiamo parlando di una maschera secolare: Farinella è nata solo nel 1953, dalla matita del grafico Mimmo Castellano. Con il suo abito a toppe colorate e il cappello a tre punte, è diventata subito l'anima allegra della città.",
    "Da dove prende il nome Farinella, la maschera simbolo di Putignano? Deriva da un alimento poverissimo ma essenziale della tradizione contadina locale: una finissima polvere ricavata da ceci e orzo tostati, condita con un pizzico di sale. Un cibo che i contadini portavano nei campi perché energetico e a lunga conservazione.",
    "A Putignano il Carnevale non si guarda, si vive. Sapevate che quasi tutta la popolazione cittadina fa parte di un'associazione o di un gruppo mascherato? Non esistono veri e propri spettatori: chiunque scenda in strada diventa parte integrante dello spettacolo, trasformando l'intero paese in un immenso e coloratissimo palcoscenico a cielo aperto.",
    "Oltre ai colossali carri di cartapesta, c'è un altro spettacolo che anima le strade di Putignano: le maschere di carattere. Si tratta di gruppi organizzati che non si limitano a sfilare, ma mettono in scena delle vere e proprie coreografie e sketch teatrali itineranti. Un teatro di strada puro, che interagisce direttamente con il pubblico dietro le transenne.",
    "Ogni anno, a Putignano, la fantasia ha una regola da rispettare. L'organizzazione del Carnevale sceglie infatti un tema centrale, come 'la satira politica', 'i miti', 'i mostri' o 'la fiaba'. Tutti i maestri cartapestai sono chiamati a ideare le loro opere colossali ruotando attorno a questo singolo concetto, creando una sfilata armoniosa ma ricca di interpretazioni uniche.",
    "Un filo invisibile e colorato unisce Putignano al resto d'Europa. Essendo il Carnevale più antico del continente, la città pugliese ha stretto forti legami e gemellaggi ufficiali con altre capitali europee del Carnevale. Uno scambio di tradizioni, maschere e maestranze che rende questa festa un vero e proprio patrimonio culturale senza confini.",
    "Vi abbiamo già parlato della 'farinella', l'antico sfarinato di ceci e orzo. Ma come si mangiava un tempo nei campi di Putignano? Essendo una polvere molto asciutta, i contadini la consumavano intingendovi dentro dei fichi secchi profumati, oppure, nei giorni di festa, la condivano con un filo d'olio d'oliva o un po' di sugo rosso. Un vero e proprio comfort food d'altri tempi!",
    "Avete in mente l'abito a losanghe del celebre Arlecchino? Ebbene, la maschera putignanese di Farinella gli somiglia molto, ma con un tocco tutto meridionale. Il suo creatore, negli anni '50, immaginò una figura a metà tra il jolly delle carte da gioco e un giullare di corte, vestendolo con un abito a toppe multicolori che rappresenta l'allegria e l'arte di arrangiarsi.",
    "Guardate bene la maschera di Farinella: il suo cappello da giullare ha esattamente tre punte, ognuna decorata con un campanellino. Non è un caso! Quelle tre punte sono un omaggio geografico: rappresentano idealmente i tre colli su cui originariamente sorgeva l'antico abitato di Putignano. Un pezzo di storia della città da indossare in testa.",
    "Cosa ci fa un pasto frugale da contadini nei menù dei ristoranti di lusso? La farinella di Putignano ha vissuto una vera e propria rinascita. Negli ultimi anni, questa polvere di legumi tostati è stata riscoperta da chef stellati e gastronomi, che la utilizzano per impanature croccanti, per addensare zuppe o per dare una nota affumicata ai piatti di alta cucina.",
    "Se passate da Putignano, preparatevi a innamorarvi dei suoi formaggi. Questa cittadina vanta una fiorente e antica tradizione casearia, basata sugli allevamenti dell'altopiano murgiano. Le mozzarelle, le burrate e soprattutto le famosissime 'trecce' di Putignano sono un'eccellenza che i pugliesi si contendono, prodotte ancora oggi con metodi artigianali.",
    "C'è un dolce, a Putignano, che profuma di mandorle e di feste di nozze. Si chiama 'Intorcinato', un biscotto tipico la cui forma ricorda una treccia, o meglio, due mani che si stringono. Nasce infatti come dolce legato ai matrimoni e alle grandi celebrazioni, preparato rigorosamente a mano e spesso accompagnato da un buon bicchiere di liquore dolce.",
    "Passeggiando per le strette viuzze del centro storico di Putignano, potreste essere rapiti da un profumo irresistibile. Il borgo conserva infatti antichi forni a legna in pietra, alcuni risalenti a secoli fa e ancora in piena attività. È qui che ogni mattina viene sfornata la classica focaccia barese, unta, croccante e ricoperta di pomodorini.",
    "La terra su cui sorge Putignano non è fatta di pianure sabbiose, ma di solida pietra. La città è adagiata sulle Murge, un vasto altopiano calcareo che domina la Puglia centrale. È un paesaggio brullo, affascinante, scolpito dall'acqua nel corso dei millenni, che regala alla città un'atmosfera sospesa e un clima fresco e asciutto.",
    "Putignano si trova in collina, ma non troppo lontana dal mare. Situata a circa 372 metri sul livello del mare, gode di una posizione strategica che le permette di avere estati ventilate e inverni frizzanti. Questa altitudine perfetta ha reso la zona da sempre ideale per l'agricoltura e, fin dall'antichità, un rifugio sicuro dalle zanzare delle coste.",
    "Chi ha fondato davvero Putignano? La storia si mescola al mito. Secondo un'antica e romantica leggenda popolare, la città prenderebbe il nome da un misterioso fondatore di origini greche, un condottiero di nome 'Potamon'. Un racconto epico che piaceva molto ai poeti locali, anche se gli storici moderni hanno ben altre teorie.",
    "C'è chi sostiene che il nome di Putignano nasconda un segreto legato agli dèi dell'Olimpo. Una teoria filologica dell'Ottocento lega infatti l'origine della città al culto di Apollo Pitico. Secondo questa ipotesi, in epoca pre-romana, ci sarebbe stato un tempio o un altare dedicato al dio del sole proprio dove oggi sorge il borgo antico.",
    "Dimenticate greci e dèi: la teoria più accreditata sull'origine di Putignano è molto più terrena. Il nome deriverebbe dal latino puteus, che significa semplicemente 'pozzo'. Il motivo? Il territorio carsico è da sempre ricchissimo di cavità, inghiottitoi e pozzi naturali che permettevano di raccogliere l'acqua piovana, rendendo questo luogo vitale per gli antichi insediamenti.",
    "Molto prima che i Romani costruissero le loro strade consolari, la terra di Putignano era già viva. Il territorio era infatti abitato dall'antica popolazione dei Peuceti, una tribù japigia che dominava la Puglia centrale. Scavi archeologici hanno riportato alla luce frammenti di ceramiche e antiche sepolture che testimoniano un passato glorioso e millenario.",
    "Nel Medioevo, Putignano non era governata da re o principi, ma da potenti uomini di fede. Il borgo fu per molto tempo un feudo gestito dai monaci Benedettini della vicina Abbazia di Santo Stefano di Monopoli. I monaci bonificarono le terre, costruirono chiese e diedero a Putignano una struttura sociale e agricola che l'ha arricchita per secoli.",
    "Immaginate cavalieri in armatura, croci a otto punte e ordini cavallereschi. Dal 1317, il controllo di Putignano passò dai monaci a un ordine militare leggendario: i Cavalieri di Malta. Questa milizia aristocratica prese il pieno controllo del feudo, trasformando il paese in un importante avamposto di potere e ricchezza nel sud Italia.",
    "Per i Cavalieri di Malta, Putignano non era un paese qualunque. Divenne una 'Balìa', ovvero una commenda, un feudo di enorme importanza strategica ed economica per l'Ordine. I Cavalieri la mantennero saldamente sotto il loro dominio per quasi cinquecento anni, governandola ininterrottamente fino all'abolizione della feudalità voluta da Napoleone nel 1806.",
    "Se guardate il centro storico di Putignano dall'alto, noterete una magia architettonica. L'antico borgo ha una perfetta forma ellittica, quasi come un uovo di pietra bianca appoggiato sulla collina. Questa forma tondeggiante era un tempo delineata da massicce mura fortificate, progettate per difendere il cuore della città da ogni attacco esterno.",
    "Oggi ci passeggiano le automobili e i pedoni, ma un tempo c'era l'acqua e il pericolo. L'antica cittadella murata di Putignano era interamente circondata da un profondo fossato difensivo. Con l'espansione moderna, il fossato è stato colmato ed è diventato l'attuale 'Estramurale', l'ampia strada ad anello che abbraccia l'intero centro storico.",
    "Per entrare nella Putignano medievale non si poteva passare da dove si voleva. L'accesso al borgo fortificato era strettamente controllato e avveniva attraverso tre sole porte monumentali. Porta Barsento, Porta Nuova e Porta Grande. Ancora oggi, attraversare questi antichi varchi significa fare un vero e proprio viaggio indietro nel tempo.",
    "Ogni città ha il suo 'cattivo' nei libri di storia. A Putignano questo ruolo spetta a Giovan Battista Carafa, signore della città nel sedicesimo secolo. Noto per i suoi pesanti soprusi e le tasse asfissianti, il Conte Carafa esasperò a tal punto i cittadini da scatenare violente rivolte popolari, dimostrando il carattere fiero e indomito dei putignanesi.",
    "Non solo goliardia e cartapesta: a Putignano batte un cuore ribelle. Quando nel 1860 l'Italia lottava per l'unità, la popolazione putignanese non stette a guardare. I cittadini parteciparono in massa e in modo molto attivo ai moti antiborbonici del Risorgimento, scrivendo una pagina importante di coraggio e patriottismo nella storia della regione.",
    "Se guardate Putignano dall'alto, vi sembrerà un normale paese collinare. Ma il vero spettacolo è sotto i vostri piedi. Il suolo di questa zona è un classico esempio di ambiente carsico: letteralmente costellato di doline, gravine e inghiottitoi profondissimi. Un vero e proprio colabrodo naturale che nasconde un mondo sotterraneo tutto da scoprire.",
    "A Putignano c'è un trullo speciale che non serve per dormire, ma per scendere al centro della terra. È l'ingresso della 'Grotta del Trullo', l'attrazione naturale più celebre della città. Un mondo ipogeo fatto di stalattiti e stalagmiti millenarie, che si apre improvvisamente proprio alle porte del centro abitato.",
    "Come si scopre una grotta spettacolare? A volte, per puro caso! La Grotta del Trullo di Putignano fu trovata casualmente nel 1931. Gli operai stavano scavando nella roccia per realizzare i condotti del nuovo acquedotto e della rete fognaria, quando improvvisamente il terreno si aprì, svelando questo incredibile scrigno sotterraneo.",
    "Perché una grotta sotterranea prende il nome da una tipica abitazione pugliese di superficie? Semplice: per proteggere l'ingresso di questa meraviglia naturale scoperta negli anni '30, venne edificato un grande trullo. Oggi, questa costruzione conica in pietra fa da suggestiva 'biglietteria' e portale d'accesso per i visitatori.",
    "Tutti conoscono le Grotte di Castellana, ma Putignano ha un primato assoluto in Puglia. Sapevate che la Grotta del Trullo è stata la primissima grotta pugliese ad essere aperta al pubblico? Fu resa accessibile e illuminata per i turisti ben prima delle sue vicine più famose, inaugurando di fatto il turismo speleologico nella regione.",
    "Scendendo nella Grotta del Trullo non troverete rocce cupe e buie, ma uno spettacolo di colori. Le formazioni calcaree all'interno brillano di incredibili sfumature rossastre e rosate. Questo effetto magico è dovuto all'altissima presenza di ossido di ferro nella roccia locale, che 'arrugginisce' l'acqua creando stalattiti color corallo.",
    "A pochi chilometri dal centro di Putignano si erge una collina verdeggiante chiamata Monte Laureto. Ma non è la cima ad attirare i visitatori, bensì il suo cuore di roccia. Qui si nasconde la Grotta di San Michele, un'altra incredibile cavità naturale che, fin da tempi antichissimi, è avvolta da un'aura di profonda spiritualità.",
    "Immaginate di entrare in una caverna e trovarvi improvvisamente in una chiesa. All'interno della Grotta di San Michele a Putignano si trova un vero e proprio santuario rupestre. Altari, affreschi e statue dedicati all'Arcangelo guerriero sono incastonati direttamente tra le stalattiti, in un'atmosfera di silenzio e devozione che fa venire i brividi.",
    "Secondo una leggenda popolare che si tramanda dal Medioevo, la Grotta di San Michele avrebbe ospitato un paziente illustre: Papa Gregorio Magno. Si narra che il pontefice si fosse rifugiato in questa umida caverna di Putignano per curarsi dalla gotta, bevendo e bagnandosi con l'acqua miracolosa che ancora oggi stilla dalle pareti di roccia.",
    "Prima degli aerei e delle navi da crociera, i pellegrini viaggiavano a piedi per mesi. Nel Medioevo, il santuario rupestre di San Michele a Putignano era una tappa fondamentale per migliaia di viandanti e crociati. Un rifugio sicuro e spirituale lungo le antiche vie che dal Nord Europa portavano verso i porti d'imbarco per la Terra Santa.",
    "Non tutte le grotte sono accoglienti. Nelle campagne putignanesi si apre una ferita nella terra conosciuta come 'Pozzo di San Nicola'. Si tratta di un gigantesco e profondo inghiottitoio naturale, un pozzo nero che per secoli ha spaventato e affascinato i contadini, alimentando storie di spiriti e leggende rurali.",
    "Putignano ha un doppio fondo. Sotto l'asfalto e i palazzi del centro storico si estende un vero e proprio labirinto. È un reticolo intricato di antichi canali sotterranei, cisterne per l'acqua piovana e immense cantine private interamente scavate a mano nella viva roccia. Una città ombra, silenziosa e affascinante.",
    "Se amate calarvi nel buio con elmetto e moschettoni, Putignano è la vostra mecca. L'intero territorio cittadino fa parte di un comprensorio speleologico vastissimo. Ci sono decine e decine di cavità ancora inesplorate o mappate solo in parte, che ogni anno attirano speleologi da tutta Italia in cerca di nuove scoperte.",
    "Nelle campagne di Putignano cresce un albero speciale: il 'fragno'. Questa maestosa quercia è un vero e proprio mistero botanico. In Italia, infatti, cresce quasi esclusivamente in questa piccola porzione di Puglia, mentre è comunissima dall'altra parte del mare, nei Balcani. Un ponte verde che unisce le due sponde dell'Adriatico.",
    "Guardando le campagne attorno a Putignano, noterete un reticolo infinito di pietre bianche. Sono i chilometri di muretti a secco che delimitano campi, uliveti e pascoli. Costruiti incastrando le pietre senza usare un briciolo di cemento, sono un'opera di ingegneria contadina talmente preziosa da essere stata dichiarata Patrimonio dell'Umanità dall'UNESCO.",
    "Il cuore spirituale e architettonico di Putignano è la Chiesa Madre, dedicata a San Pietro Apostolo. Affacciata su una suggestiva piazzetta del centro storico, è il baricentro della vita cittadina. La sua possente torre campanaria svetta sui tetti bianchi, segnando lo scorrere del tempo per tutti i putignanesi.",
    "La Chiesa Madre di Putignano è un edificio con doppia personalità. Se vi fermate all'esterno, ammirerete un austero e massiccio portale di epoca romanica. Ma appena varcate la soglia... sorpresa! L'interno è stato pesantemente rimaneggiato nei secoli successivi e vi accoglierà con un trionfo di stucchi, marmi e decorazioni in puro stile barocco.",
    "C'è una chiesa a Putignano che custodisce il tesoro più importante della città. È la chiesa di Santa Maria la Greca, un gioiello di eleganza. Al suo interno, in un prezioso reliquiario, è conservato un frammento del cranio di Santo Stefano Protomartire. Proprio la reliquia che, secoli fa, ha dato origine alla festa del Carnevale.",
    "A Putignano, la storia si respira nei palazzi. Il 'Palazzo del Balì' è uno degli edifici più imponenti e affascinanti del borgo antico. Per secoli non è stato una semplice casa, ma la sfarzosa residenza ufficiale del Governatore dei Cavalieri di Malta. Un vero e proprio palazzo del potere, con stanze affrescate e ampi cortili.",
    "Nella piazza principale del borgo antico di Putignano sorge un edificio piccolo ma denso di storia: il Sedile. Questa elegante struttura, di fronte al Palazzo del Balì, era l'antico municipio cittadino. Era il luogo dove i rappresentanti del popolo si riunivano per prendere le decisioni importanti per la vita della comunità.",
    "Se alzate gli occhi verso il palazzo del Sedile a Putignano, noterete una bellissima loggia scenografica. Proprio in cima a questa struttura fa bella mostra di sé l'orologio storico della città. Per secoli, i suoi rintocchi hanno regolato i turni di lavoro nei campi e i momenti di riposo degli artigiani del borgo.",
    "Volete sapere come viveva una ricca famiglia pugliese dell'Ottocento? A Putignano basta entrare nel Museo Civico Romanazzi Carducci. Ospitato nel palazzo della storica famiglia nobiliare, questo museo è una macchina del tempo che vi farà passeggiare tra salotti eleganti, carte da parati d'epoca e atmosfere da Gattopardo.",
    "Il Museo Romanazzi Carducci di Putignano non è fatto solo di mobili antichi. Al suo interno, oltre agli arredi originali perfettamente conservati, potrete ammirare una vasta e curiosa collezione di armi d'epoca, strumenti musicali e l'incredibile archivio storico della famiglia, che racconta secoli di intrighi e affari nel sud Italia.",
    "Cosa succede quando un ex convento chiude le porte alla religione e le apre alla cultura? A Putignano, l'antico convento delle Carmelitane è stato sapientemente restaurato. Il suo elegante chiostro interno, un tempo regno del silenzio, oggi è una vivace piazza coperta utilizzata come centro culturale e sede della ricca biblioteca comunale.",
    "Se andate a Putignano, indossate scarpe comode e guardate per terra. Molte vie del centro storico mantengono ancora intatta la 'Chiancata'. Si tratta della pavimentazione originale fatta di 'chianche', enormi basole di pietra calcarea bianca lisciate dal passaggio di milioni di passi nel corso dei secoli. Un tappeto di pietra che riflette la luce del sole.",
    "Sapevate che Putignano non è solo la città del Carnevale, ma anche quella dell'amore? A partire dal secondo dopoguerra, questo borgo pugliese si è trasformato in un polo di eccellenza internazionale per l'industria degli abiti da sposa. Una vera e propria 'capitale del wedding', dove l'alta sartoria locale ha vestito i sogni di migliaia di spose in tutto il mondo.",
    "Accanto ai sontuosi abiti nuziali, le macchine da cucire di Putignano hanno fatto la storia in un altro settore. Per decenni, la cittadina è stata considerata un distretto industriale primario per la produzione di moda per bambini e abbigliamento per l'infanzia. Un'eccellenza tessile che ha dato lavoro a intere generazioni di sarte e modelliste.",
    "Abbiamo detto che il Carnevale inizia il 26 dicembre per celebrare Santo Stefano. Ma a Putignano, il Santo Patrono si festeggia in grande stile anche sotto il sole cocente! Il 3 agosto la città si ferma per la festa patronale estiva, un tripudio di luminarie, bande musicali e fuochi d'artificio che illumina a giorno le calde notti pugliesi.",
    "Ogni città del sud che si rispetti ha una fortissima devozione mariana. A Putignano, l'amata co-patrona è Maria Santissima del Pozzo. A lei è dedicata una festa sentitissima alla fine di agosto, e la sua figura è strettamente legata all'elemento più prezioso e raro di questo territorio carsico: l'acqua dolce.",
    "La venerazione per la Madonna del Pozzo nasce da una storia di disperazione e speranza. Si narra che il suo culto esplose dopo il ritrovamento miracoloso di un'icona mariana durante un periodo di gravissima e prolungata siccità che stava mettendo in ginocchio i raccolti. Un vero e proprio salvataggio divino impresso nella memoria del paese.",
    "Se parlate con un barese, un monopolitano e un putignanese, noterete subito la differenza. Il dialetto di Putignano è particolarissimo e unico nel suo genere. È caratterizzato da una pronunciata chiusura dei suoni vocalici che lo rende quasi musicale, a tratti spigoloso, e immediatamente riconoscibile rispetto alle parlate dei paesi limitrofi.",
    "Passeggiando nel centro storico di Putignano, potreste camminare sopra antiche fabbriche senza saperlo. Sotto molti palazzi nobiliari del borgo antico si celano ancora oggi vecchi frantoi ipogei. Erano enormi macine per l'olio d'oliva ricavate scavando direttamente nella roccia sotterranea, dove le temperature costanti favorivano la conservazione dell'oro verde.",
    "Non solo grano e ulivi. Le campagne attorno a Putignano, insieme a quelle della vicina Turi, sono rinomate in tutta Italia per una delizia rossa e succosa: la 'Ciliegia Ferrovia'. Questa varietà, grande, croccante e dolcissima, è il vanto dell'agricoltura locale e colora i mercati del sud tra maggio e giugno.",
    "Se cercate un campo base per esplorare la Puglia, Putignano è la scelta perfetta. La città si trova infatti al centro di una ragnatela di comuni turisticamente fantastici. Confina a un passo con i trulli di Alberobello, le grotte di Castellana, i boschi di Noci, il castello di Gioia del Colle e la storia di Conversano.",
    "A Putignano non c'è solo il Carnevale a richiamare migliaia di visitatori. Negli ultimi anni, il borgo si è trasformato in una meta imperdibile anche durante le feste invernali, grazie a un progetto chiamato 'Borgo Illuminato'. Installazioni luminose, opere d'arte visiva e mercatini riempiono di magia i vicoli del centro storico aspettando il Capodanno.",
    "L'arte a Putignano non è solo cartapesta e non si ferma in centro. La città è diventata un museo a cielo aperto grazie a svariati progetti di 'Street Art'. Artisti di fama internazionale hanno colorato interi quartieri periferici, come il rione San Pietro Piturno, trasformando grigi palazzi popolari in gigantesche tele ricche di messaggi sociali.",
    "Immergersi nei vicoli di Putignano è come fare un salto nel passato. Lontano dalle vie dello shopping moderno, resistono ancora piccole botteghe artigiane dove il tempo sembra essersi fermato. Falegnami, calzolai e restauratori lavorano a porte aperte, lasciando che il rumore degli attrezzi e il profumo del legno invadano la strada.",
    "C'è un pezzo di Putignano dall'altra parte dell'Oceano Atlantico. Tra la fine dell'Ottocento e i primi del Novecento, una fortissima ondata migratoria portò tantissimi putignanesi a cercare fortuna nelle Americhe. Moltissimi si stabilirono in Argentina, dove ancora oggi vivono intere comunità che tramandano il dialetto e le tradizioni della madrepatria.",
    "Pensate che i trulli siano solo le piccole casette di Alberobello? Sbagliato! Le campagne di Putignano offrono complessi agricoli unici e imponenti: le 'masserie a trullo'. Si tratta di vere e proprie aziende agricole fortificate, circondate da muretti a secco e formate da decine di trulli giganti collegati tra loro. Un'architettura rurale maestosa.",
    "Sei secoli di Carnevale non passano inosservati. Questo rito ha forgiato in modo indelebile il carattere dei putignanesi. I cittadini sono famosi in tutta la regione per la loro ospitalità, la battuta sempre pronta e, soprattutto, una sana e feroce autoironia. A Putignano prendersi in giro non è un'offesa, è un'arte.",
    "Il 2 febbraio, giorno della Candelora, a Putignano si guarda il cielo per interrogare un orso! È la tradizionale 'Festa dell'Orso', una pantomima in cui un attore travestito da plantigrado viene portato in piazza. La leggenda vuole che se il tempo è bello l'orso si costruisce il pagliaio (l'inverno durerà ancora), se piove o nevica... l'inverno è finito!",
    "Quando le piazze del Sud Italia si accendono a festa, c'è spesso lo zampino di un putignanese. La città vanta infatti storiche famiglie di 'paratori', ovvero artigiani maestri nella costruzione delle tradizionali luminarie in legno. Enormi cattedrali di luce colorata che, da Putignano, viaggiano per illuminare le feste patronali di tutto il mondo.",
    "Il centro storico di Putignano non è un labirinto casuale, ma è costruito su tre anelli concentrici chiamati 'i tre giri'. Un tempo rispondevano a rigide regole sociali e di difesa: nel giro più interno c'erano i palazzi del potere e le chiese, in quello mediano le abitazioni dei benestanti, e in quello esterno, a ridosso delle mura, le case del popolo.",
    "Come si fa a mantenere in vita il Carnevale più antico d'Europa? Semplice: lo si insegna ai bambini. A Putignano la lavorazione della cartapesta è una cosa seria, tanto che spesso vengono organizzati veri e propri laboratori didattici nelle scuole. I maestri artigiani svelano i segreti di colla e carta di giornale, formando le generazioni del futuro.",
    "Immaginate di preparare il pane a casa, ma di non avere il forno per cuocerlo. Fino a pochi decenni fa, a Putignano era la normalità. Le donne preparavano gli impasti di pane e focacce nelle proprie cucine e poi li portavano nei grandi forni a legna di quartiere, incidendo le proprie iniziali sulla pasta per non confonderli con quelli dei vicini.",
    "Tra tutti i Giovedì del Carnevale putignanese, quello 'dei Pazzi' è forse il più imprevedibile. In questa giornata la goliardia regna sovrana e le regole vengono sovvertite. Per strada è facile imbattersi in improvvisate bande di giovani che coinvolgono i passanti in scherzi e balli, celebrando la sana e pura follia liberatoria.",
    "Se camminate con il naso all'insù nel centro storico di Putignano, noterete tantissime 'edicole votive'. Sono piccoli altari incastonati nei muri dei palazzi o agli angoli delle strade, che ospitano dipinti o statuette di santi. Un tempo, la fiammella della loro candela era l'unica vera illuminazione notturna per chi rincasava nel buio.",
    "Putignano è in collina, ma il suo destino è sempre stato legato all'acqua salata. Per secoli, la città ha avuto un rapporto di amore e rivalità commerciale con la vicina e costiera Monopoli. Da lì arrivavano le reliquie di Santo Stefano, e sempre da lì, dal suo porto, partivano le merci agricole putignanesi verso l'Oriente.",
    "Non si può lasciare Putignano senza un piccolo pezzo di Carnevale. I maestri cartapestai, durante il resto dell'anno, mettono da parte i carri colossali e si dedicano alle miniature. Realizzano piccole e dettagliatissime statuette in cartapesta della maschera di Farinella, che diventano dei souvenir preziosi e interamente fatti a mano.",
    "E chiudiamo con una regola non scritta. A Putignano, durante il Carnevale, è impossibile restare fermi. Che sia intorno al carro della Campana dei Maccheroni o tra i gruppi in maschera, prima o poi qualcuno vi prenderà per mano e vi trascinerà in un ballo di piazza. È l'essenza di questa terra: un invito alla vita, alla gioia e alla condivisione.",
]

JUNK_RE = re.compile(
    r"cookie|privacy policy|diritti riservati|p\.iva|partita iva|sede legale"
    r"|copyright|newsletter|abbonati|registrati|gdpr|informativa"
    r"|advertising|sponsored|scarica l.app|seguici su|condividi"
    r"|seleziona.*opzioni|gestione delle impostazioni|g\.co/privacytools"
    r"|prima di procedere|conferma la tua scelta|acconsenti",
    re.IGNORECASE)

STOPWORDS = {
    "il","lo","la","i","gli","le","un","uno","una","di","a","da","in","su",
    "per","tra","fra","e","o","ma","che","con","del","della","dei","delle",
    "al","alla","ai","alle","nel","nella","nei","nelle","sul","sulla","sui",
    "ha","sono","hanno","era","si","non","anche","come","dove","quando",
    "mentre","dopo","prima","poi","tutto","tutti","questo","questa","loro",
}

# ============================================================
# UTILITY COMUNI
# ============================================================

def strip_html(s):
    s = html.unescape(str(s))
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def normalize(s):
    s = strip_html(s).lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return " ".join(w for w in s.split() if w not in STOPWORDS and len(w) > 2)

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def is_junk(t):
    return bool(JUNK_RE.search(t))

def is_italian(t):
    en = {"the","and","for","this","that","with","from","have","you","are",
          "was","were","they","will","click","accept","consent","cookies"}
    words = t.lower().split()
    if not words: return True
    return sum(1 for w in words if w in en) / len(words) < 0.20

def parse_rss_date(e):
    for attr in ("published_parsed", "updated_parsed"):
        tm = getattr(e, attr, None)
        if tm:
            try: return datetime(*tm[:6], tzinfo=timezone.utc)
            except: pass
    return None

def pulisci_testo(s):
    s = strip_html(s).strip()
    s = re.sub(r"\b(FOTO|VIDEO|GALLERY|FOTOGALLERY|AUDIO|PODCAST|LIVE|BREAKING)\b\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\.{2,}|\u2026", "", s)
    s = s.rstrip(". ")
    s = re.sub(r"\.\s+([a-zA-Z\xe0-\xff])", lambda m: ", " + m.group(1), s)
    s = re.sub(r"\.(\s|$)", r"\1", s)
    s = re.sub(r"[\xab\xbb\u201c\u201d\u201e]", '"', s)
    s = re.sub(r"(?<!\w)['\u2018]{2}(.+?)['\u2019]{2}(?!\w)", r'"\1"', s)
    return re.sub(r"\s+", " ", s).strip()

def pulisci_desc(desc, max_car=500):
    d = strip_html(desc).strip()
    d = re.sub(r"\s*L[''']articolo\s.{0,120}\sproviene\sda\s.{0,60}\.?\s*$", "", d, flags=re.IGNORECASE)
    d = re.sub(r"\s*,?\s*(Secondo quanto diffuso|Da dettagliare|Leggi anche|Fonte:|Per saperne di pi).{0,200}$",
               "", d, flags=re.IGNORECASE)
    d = re.sub(r"\s+", " ", d).strip()
    frammenti = re.split(r",\s*", d)
    if len(frammenti) > 3:
        primo = frammenti[0].lower()
        utili = [frammenti[0]]
        for f in frammenti[1:]:
            if len(f.strip()) < 15: continue
            if SequenceMatcher(None, f.lower()[:50], primo[:50]).ratio() > 0.55: continue
            utili.append(f)
            if sum(len(u) for u in utili) >= max_car: break
        d = ", ".join(utili)
    if len(d) > max_car:
        for sep in (", ", ". ", " "):
            pos = d[:max_car].rfind(sep)
            if pos > 60:
                d = d[:pos]
                break
    return d.strip().rstrip(".,; ")

def normalizza_per_tts(testo: str) -> str:
    """
    Converte sigle puntate in sigle leggibili dal TTS.
    Esempi: I.R.C.C.S. → IRCCS,  S.p.A. → SpA,  D.O.C. → DOC
    Gestisce anche trattini nei nomi di città: Castellana-Grotte → Castellana Grotte
    """
    # Sigle tutto maiuscolo con punti: I.R.C.C.S. → IRCCS
    testo = re.sub(r'\b([A-Z])(?:\.([A-Z]))+\.?', lambda m: m.group(0).replace('.', ''), testo)
    # Sigle miste tipo S.p.A. → SpA, S.r.l. → Srl
    testo = re.sub(r'\b([A-Za-z])\.([A-Za-z])\.([A-Za-z])\.?', lambda m: m.group(0).replace('.', ''), testo)
    # Trattini in nomi di comuni/luoghi (Castellana-Grotte → Castellana Grotte)
    testo = re.sub(r'([A-Z][a-zà-ÿ]+)-([A-Z][a-zà-ÿ]+)', r'\1 \2', testo)
    return testo

def fetch_article_text(url, max_car=600, domini_no_fetch=None):
    if not HAS_REQUESTS or not url: return ""
    if domini_no_fetch is None: domini_no_fetch = set()
    try:
        from urllib.parse import urlparse
        dominio = urlparse(url).netloc.lower().lstrip("www.")
        if dominio in {d.lstrip("www.") for d in domini_no_fetch}: return ""
    except Exception: return ""
    try:
        r = requests.get(url, headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        if "text/html" not in r.headers.get("content-type", ""): return ""
        raw = r.text
        if any(kw in raw for kw in ["g.co/privacytools","consent.google","Before you continue",
                                     "Seleziona \u201cAltri opzioni\u201d"]): return ""
        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script","style","nav","header","footer","aside","form","button","noscript","iframe"]):
            tag.decompose()
        paragrafi = []
        for sel in ["article p",".content p",".post-content p",".entry-content p","main p","p"]:
            paragrafi = soup.select(sel)
            if paragrafi: break
        testi = []
        for p in paragrafi:
            txt = strip_html(p.get_text()).strip()
            if len(txt) < 40 or is_junk(txt) or not is_italian(txt): continue
            testi.append(txt)
            if sum(len(t) for t in testi) >= max_car: break
        return " ".join(testi)[:max_car]
    except Exception: return ""

def topic_words(s):
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return set(w for w in s.split() if w not in STOPWORDS and len(w) > 3)

def stesso_topic(it1, it2, soglia=3, generiche=None):
    if generiche is None:
        generiche = {"notizie","aggiornamento","ultime","edizione","oggi","ieri","anno",
                     "gennaio","febbraio","marzo","aprile","maggio","giugno",
                     "luglio","agosto","settembre","ottobre","novembre","dicembre"}
    blob1 = topic_words(it1["title"] + " " + it1.get("desc",""))
    blob2 = topic_words(it2["title"] + " " + it2.get("desc",""))
    comuni = (blob1 & blob2) - generiche
    return len(comuni) >= soglia

def deduplica(items):
    seen_links, seen_norms, seen_sources, unique = set(), [], set(), []
    for it in items:
        link = it.get("link","")
        if link and link in seen_links: continue
        norm = it["norm"]
        if norm in seen_norms: continue
        if any(similarity(norm, sn) > 0.55 for sn in seen_norms): continue
        if any(stesso_topic(it, u) for u in unique): continue
        if it["source"] in seen_sources: continue
        if link: seen_links.add(link)
        seen_norms.append(norm)
        seen_sources.add(it["source"])
        unique.append(it)
    return unique

def fetch_rss_generic(name, url, weight, cutoff, filter_fn=None):
    if not HAS_FEEDPARSER: return []
    results = []
    try:
        feed = feedparser.parse(url)
        if getattr(feed,"bozo",False) and not getattr(feed,"entries",[]): return []
        for pos, e in enumerate(feed.entries[:40]):
            title_raw   = strip_html(getattr(e,"title",""))
            summary_raw = strip_html(getattr(e,"summary","") or "")
            blob = (title_raw + " " + summary_raw).lower()
            if not title_raw: continue
            if not is_italian(blob): continue
            if is_junk(blob): continue
            if filter_fn and not filter_fn(blob): continue
            dt = parse_rss_date(e)
            if dt and cutoff and dt < cutoff: continue
            clean_title = re.split(r"\s[-\u2013\u2014]\s[A-Z]", title_raw)[0].strip()
            link = strip_html(getattr(e,"link","") or "")
            if is_junk(summary_raw): summary_raw = ""
            results.append({
                "source": name, "weight": weight, "pos": pos,
                "dt": dt, "title": clean_title, "desc": summary_raw,
                "link": link, "norm": normalize(clean_title),
            })
    except Exception: pass
    return results

# ============================================================
# MODULO ONOMASTICI
# ============================================================

def get_onomastico() -> str:
    chiave = datetime.now().strftime("%d/%m")
    return ONOMASTICI_DB.get(chiave, "")

# ============================================================
# MODULO INTESTAZIONE
# ============================================================

def get_intestazione() -> list:
    oggi   = datetime.now()
    giorno = GIORNI_ITA[oggi.weekday()]
    data   = f"{oggi.day} {MESI_ITA[oggi.month]} {oggi.year}"
    ora    = f"Sono le {oggi.hour} e {oggi.minute:02d}." if oggi.minute != 0 else f"Sono le {oggi.hour} in punto."
    santo  = get_onomastico()
    riga_data = f"Oggi è {giorno} {data}, {santo}. {ora}" if santo else f"Oggi è {giorno} {data}. {ora}"

    return [
        "[T] [M] Buongiorno Putignano.",
        "",
        "[T] [F] Benvenuti nel nostro podcast quotidiano. " + riga_data,
        "",
    ]

# ============================================================
# MODULO METEO  (da MeteoNews.py)
# ============================================================

LAT_PUT  = 40.8487
LON_PUT  = 17.1275
TZ_PUT   = "Europe/Rome"

OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude={lat}&longitude={lon}"
    "&hourly=temperature_2m,precipitation_probability,weathercode,windspeed_10m,relativehumidity_2m"
    "&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,precipitation_probability_max"
    "&timezone={tz}&forecast_days=3"
)

WMO_DESC = {
    0:"cielo sereno", 1:"prevalentemente sereno", 2:"parzialmente nuvoloso", 3:"cielo coperto",
    45:"nebbia", 48:"nebbia con brina",
    51:"pioggerella leggera", 53:"pioggerella moderata", 55:"pioggerella intensa",
    61:"pioggia leggera", 63:"pioggia moderata", 65:"pioggia intensa",
    71:"neve leggera", 73:"neve moderata", 75:"neve intensa", 77:"granuli di neve",
    80:"rovesci leggeri", 81:"rovesci moderati", 82:"rovesci violenti",
    85:"nevicate leggere", 86:"nevicate abbondanti",
    95:"temporale", 96:"temporale con grandine leggera", 99:"temporale con grandine intensa",
}

FASCE_OGGI   = [(6,11,"questa mattina"),(12,13,"a mezzogiorno"),(14,18,"questo pomeriggio"),(19,22,"questa sera"),(23,5,"questa notte")]
FASCE_DOMANI = [(6,11,"domani mattina"),(12,13,"domani a mezzogiorno"),(14,18,"domani pomeriggio"),(19,22,"domani sera"),(23,5,"domani notte")]

def wmo_desc(code):
    return WMO_DESC.get(int(code) if code is not None else 0, "condizioni variabili")

def _ora_in_fascia(h, inizio, fine):
    if inizio <= fine: return inizio <= h <= fine
    return h >= inizio or h <= fine

def analizza_fasce_meteo(ore_data, ora_inizio):
    oggi   = ora_inizio.date()
    domani = oggi + timedelta(days=1)
    blocchi = []
    for is_domani, data_target, fasce in [(False, oggi, FASCE_OGGI), (True, domani, FASCE_DOMANI)]:
        for inizio, fine, label in fasce:
            ore_fascia = [v for dt, v in ore_data.items()
                          if dt.date() == data_target
                          and _ora_in_fascia(dt.hour, inizio, fine)
                          and (is_domani or dt > ora_inizio)]
            if not ore_fascia: continue
            blocchi.append({
                "label":  label,
                "temp":   round(sum(v["temp"]   for v in ore_fascia) / len(ore_fascia)),
                "precip": round(max(v["precip"] for v in ore_fascia)),
                "wcode":  Counter(v["wcode"] for v in ore_fascia).most_common(1)[0][0],
                "wind":   round(max(v["wind"]   for v in ore_fascia)),
            })
    return blocchi

def costruisci_tts_meteo(blocchi, tmin_oggi, tmax_oggi, tmin_dom, tmax_dom):
    if not blocchi: return "Al momento non sono disponibili previsioni meteo per Putignano."
    LABEL_OGGI   = {"questa mattina","a mezzogiorno","questo pomeriggio","questa sera","questa notte"}
    LABEL_DOMANI = {"domani mattina","domani a mezzogiorno","domani pomeriggio","domani sera","domani notte"}
    oggi_b   = [b for b in blocchi if b["label"] in LABEL_OGGI]
    domani_b = [b for b in blocchi if b["label"] in LABEL_DOMANI]
    frasi = []
    if oggi_b:
        wcode = Counter(b["wcode"] for b in oggi_b).most_common(1)[0][0]
        pioggia = max(b["precip"] for b in oggi_b)
        f = f"Oggi {wmo_desc(wcode)}"
        if tmin_oggi is not None and tmax_oggi is not None:
            f += f", con temperature tra {tmin_oggi} e {tmax_oggi} gradi"
        if pioggia >= 45: f += " e probabilità di pioggia"
        elif pioggia >= 20: f += " e qualche possibilità di pioggia"
        frasi.append(f + ".")
    if domani_b:
        wcode = Counter(b["wcode"] for b in domani_b).most_common(1)[0][0]
        pioggia = max(b["precip"] for b in domani_b)
        f = f"Per domani è previsto {wmo_desc(wcode)}"
        if tmin_dom is not None and tmax_dom is not None:
            f += f", con temperature tra {tmin_dom} e {tmax_dom} gradi"
        if pioggia >= 45: f += " e probabilità di pioggia"
        elif pioggia >= 20: f += " e qualche possibilità di pioggia"
        frasi.append(f + ".")
    return re.sub(r"\s+", " ", " ".join(frasi)).strip()

def get_meteo() -> str:
    if not HAS_REQUESTS: return "Servizio meteo non disponibile."
    url = OPEN_METEO_URL.format(lat=LAT_PUT, lon=LON_PUT, tz=TZ_PUT)
    try:
        r = requests.get(url, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        dati = r.json()
    except Exception as ex:
        return f"Impossibile recuperare il meteo: {ex}"

    hourly = dati.get("hourly", {})
    daily  = dati.get("daily",  {})
    times  = hourly.get("time", [])
    temps  = hourly.get("temperature_2m", [])
    precips= hourly.get("precipitation_probability", [])
    wcodes = hourly.get("weathercode", [])
    winds  = hourly.get("windspeed_10m", [])

    try:
        import zoneinfo
        zona = zoneinfo.ZoneInfo("Europe/Rome")
    except ImportError:
        zona = None

    ora_now = datetime.now(timezone.utc).astimezone(zona) if zona else datetime.now()
    ora_inizio = ora_now.replace(minute=0, second=0, microsecond=0)

    ore_data = {}
    for i, t in enumerate(times):
        try:
            dt = datetime.fromisoformat(t)
            if zona: dt = dt.replace(tzinfo=zona) if dt.tzinfo is None else dt.astimezone(zona)
        except Exception: continue
        ore_data[dt] = {
            "temp":   temps[i]   if i < len(temps)   else 15,
            "precip": precips[i] if i < len(precips) else 0,
            "wcode":  wcodes[i]  if i < len(wcodes)  else 0,
            "wind":   winds[i]   if i < len(winds)   else 0,
        }

    d_times = daily.get("time", [])
    d_tmax  = daily.get("temperature_2m_max", [])
    d_tmin  = daily.get("temperature_2m_min", [])
    oggi_s  = ora_inizio.date().isoformat()
    dom_s   = (ora_inizio.date() + timedelta(days=1)).isoformat()

    tmin_oggi = tmax_oggi = tmin_dom = tmax_dom = None
    for i, dt in enumerate(d_times):
        if dt == oggi_s:
            tmin_oggi = round(d_tmin[i]) if i < len(d_tmin) else None
            tmax_oggi = round(d_tmax[i]) if i < len(d_tmax) else None
        elif dt == dom_s:
            tmin_dom  = round(d_tmin[i]) if i < len(d_tmin) else None
            tmax_dom  = round(d_tmax[i]) if i < len(d_tmax) else None

    blocchi = analizza_fasce_meteo(ore_data, ora_inizio)
    return costruisci_tts_meteo(blocchi, tmin_oggi, tmax_oggi, tmin_dom, tmax_dom)

# ============================================================
# MODULO FARMACIE  (da FarmacieNews.py)
# ============================================================

FARMACIE_URL = "https://www.informatissimo.net/utilita/farmacie-di-turno-putignano.html"
GUARDIA_MEDICA = "0 8 0   5 8 4 0 8 1 5"
MONTHS_MAP = {"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,"giugno":6,
              "luglio":7,"agosto":8,"settembre":9,"ottobre":10,"novembre":11,"dicembre":12}
MONTHS_MAP_INV = {v: k for k, v in MONTHS_MAP.items()}

def get_farmacie() -> str:
    if not HAS_REQUESTS:
        return f"Dati farmacie non disponibili, Guardia Medica: {GUARDIA_MEDICA}"
    oggi = datetime.now().date()
    try:
        r = requests.get(FARMACIE_URL, headers=HTTP_HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        testo = soup.get_text("\n", strip=True)
        testo = "\n".join(re.sub(r" {2,}", " ", l) for l in testo.splitlines())

        pat = re.compile(
            r"(?:lunedì|martedì|mercoledì|giovedì|venerdì|sabato|domenica)?\s*"
            r"(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
            r"settembre|ottobre|novembre|dicembre)\s+(20\d{2})\s+"
            r"(Farmacia\s+.+?)(?=\s+chiama|\s+\d{1,2}\s+\w+\s+20\d{2}|$)",
            re.IGNORECASE | re.MULTILINE)

        def parse_entry(m):
            g = int(m.group(1))
            mese = MONTHS_MAP.get(m.group(2).lower(), 0)
            anno = int(m.group(3))
            farmacia = re.sub(r"\s+", " ", m.group(4)).strip()
            farmacia = re.sub(r"\s+(Via|Viale|Piazza|Corso|Largo|Vicolo|P\.za)\b.*$", "", farmacia, flags=re.IGNORECASE).strip()
            try: return date(anno, mese, g), farmacia
            except: return None, farmacia

        def accorpa(entries):
            if not entries: return ""
            blocchi = []
            inizio, fine, farm_cur = entries[0][0], entries[0][0], entries[0][1]
            for dt, farm in entries[1:]:
                if farm.lower() == farm_cur.lower() and dt == fine + timedelta(days=1):
                    fine = dt
                else:
                    blocchi.append((inizio, fine, farm_cur))
                    inizio, fine, farm_cur = dt, dt, farm
            blocchi.append((inizio, fine, farm_cur))
            parti = []
            for ini, fin, farm in blocchi:
                ms = MONTHS_MAP_INV[ini.month]
                if ini == fin: parti.append(f"il {ini.day} {ms}: {farm}")
                elif ini.month == fin.month: parti.append(f"dal {ini.day} al {fin.day} {ms}: {farm}")
                else: parti.append(f"dal {ini.day} {ms} al {fin.day} {MONTHS_MAP_INV[fin.month]}: {farm}")
            return ", poi ".join(parti)

        all_entries = [(d, f) for m in pat.finditer(testo) for d, f in [parse_entry(m)] if d]
        entries_da_oggi = [(d, f) for d, f in all_entries if d >= oggi]
        if entries_da_oggi and entries_da_oggi[0][0] == oggi:
            return f"Farmacia di turno a Putignano: {accorpa(entries_da_oggi)}"
        prossime = [(d, f) for d, f in all_entries if d > oggi]
        if prossime:
            return f"Nessun turno farmacia per oggi a Putignano, prossimi turni: {accorpa(prossime[:6])}"
        return f"Informazioni farmacie di turno non trovate, Guardia Medica: {GUARDIA_MEDICA}"
    except Exception:
        return f"Servizio farmacie temporaneamente non disponibile, Guardia Medica: {GUARDIA_MEDICA}"

# ============================================================
# MODULO ITALIA NEWS  (da ItaliaNews.py)
# ============================================================

ITALIA_N_NOTIZIE     = 5
ITALIA_PRIMARY_HOURS = 24
ITALIA_FALLBACK_DAYS = 7
ITALIA_MAX_WAIT      = 35

ITALIA_NO_FETCH = {"news.google.com","www.bing.com","bing.com","news.bing.com","google.com","www.google.com"}

ITALIA_RSS = [
    ("RaiNews",       "https://www.rainews.it/dl/rainews/media/ContentItem-3156f2f2-dc70-4953-8e2f-70d7489d4ce9-rss.xml", 1.00),
    ("ANSA-Top",      "https://www.ansa.it/sito/notizie/topnews/topnews_rss.xml",                                         1.00),
    ("Corriere",      "https://xml2.corrieredellasera.it/rss/homepage.xml",                                               0.95),
    ("Repubblica",    "https://www.repubblica.it/rss/homepage/rss2.0.xml",                                               0.95),
    ("Sole24Ore",     "https://www.ilsole24ore.com/rss/italia--ultime-notizie.xml",                                       0.90),
    ("SkyTG24",       "https://tg24.sky.it/feed/tg24-home.xml",                                                          0.90),
    ("TgCom24",       "https://www.tgcom24.mediaset.it/rss/tgcom.rss",                                                   0.88),
    ("Fanpage",       "https://www.fanpage.it/feed/",                                                                    0.85),
    ("IlFatto",       "https://www.ilfattoquotidiano.it/feed/",                                                           0.85),
    ("Stampa",        "https://www.lastampa.it/rss",                                                                     0.83),
    ("HuffPost",      "https://www.huffingtonpost.it/feeds/index.xml",                                                   0.80),
    ("Messaggero",    "https://www.ilmessaggero.it/rss/home.xml",                                                        0.80),
    ("GoogleNews-IT", "https://news.google.com/rss?hl=it&gl=IT&ceid=IT:it",                                              0.75),
]

def componi_frase_italia(title, desc):
    t = pulisci_testo(title)
    d = pulisci_testo(pulisci_desc(desc, max_car=280))
    if t and d:
        base = d if d.lower().startswith(t[:25].lower()) else (t + ": " + d if d[0].isupper() else t + ", " + d)
    elif t: base = t
    else:   base = d
    if len(base) < 280:
        tl = base.lower()
        if any(w in tl for w in ["morto","morta","ucciso","omicidio","strage","attentato"]):
            coda = "una notizia che ha scosso l'opinione pubblica italiana"
        elif any(w in tl for w in ["governo","ministro","parlamento","decreto","legge","senato"]):
            coda = "un aggiornamento dal fronte politico nazionale"
        elif any(w in tl for w in ["economia","pil","inflazione","mercati","spread","borsa"]):
            coda = "un aggiornamento dalla scena economica italiana"
        elif any(w in tl for w in ["terremoto","alluvione","incendio","emergenza","maltempo"]):
            coda = "una notizia che riguarda la sicurezza del territorio nazionale"
        elif any(w in tl for w in ["calcio","serie","juventus","milan","inter","napoli","sport"]):
            coda = "un aggiornamento dal mondo dello sport italiano"
        elif any(w in tl for w in ["processo","arresti","indagine","tribunale","condanna"]):
            coda = "una notizia dal fronte giudiziario italiano"
        elif any(w in tl for w in ["sanità","ospedal","vaccin","malattia","cure","medic"]):
            coda = "un aggiornamento dal settore della sanità nazionale"
        else:
            coda = "una delle notizie più seguite in Italia nelle ultime ore"
        base = base + ", " + coda
    if len(base) > 430:
        for sep in (", ", "; "):
            pos = base[:430].rfind(sep)
            if pos > 180:
                base = base[:pos]
                break
    base = re.sub(r"\s+", " ", base).strip()
    if base and not base.endswith("."): base += "."
    return normalizza_per_tts(base)

def score_italia(item, now):
    s = item["weight"]
    if item.get("dt"):
        age_h = max(0, (now - item["dt"]).total_seconds() / 3600)
        s *= max(0.3, 1 - age_h / (3 * 24))
    s *= 1 + max(0, (10 - item.get("pos", 10)) / 10) * 0.15
    return s

def get_notizie_italia(n=ITALIA_N_NOTIZIE):
    now_utc = datetime.now(timezone.utc)
    top = []
    for ore in [ITALIA_PRIMARY_HOURS, ITALIA_FALLBACK_DAYS * 24]:
        cutoff = now_utc - timedelta(hours=ore)
        raw = []
        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = {ex.submit(fetch_rss_generic, nm, url, w, cutoff): nm
                       for nm, url, w in ITALIA_RSS}
            done, not_done = wait(futures, timeout=ITALIA_MAX_WAIT)
            for f in done:
                try: raw.extend(f.result())
                except: pass
            for f in not_done: f.cancel()
        # Arricchisci desc corte
        for it in raw:
            if len(it["desc"]) < 120 and it.get("link"):
                extra = fetch_article_text(it["link"], max_car=350, domini_no_fetch=ITALIA_NO_FETCH)
                if extra and len(extra) > len(it["desc"]): it["desc"] = extra
        top = sorted(deduplica(raw), key=lambda it: score_italia(it, now_utc), reverse=True)
        if len(top) >= n: break
    return [{"title": it["title"], "desc": it["desc"],
             "testo_tts": componi_frase_italia(it["title"], it["desc"]),
             "link": it.get("link",""), "source": it["source"], "dt": it.get("dt")}
            for it in top[:n]]

# ============================================================
# MODULO PUTIGNANO NEWS  (da PutignanoNews.py v7)
# ============================================================

PUT_N_NOTIZIE     = 3
PUT_PRIMARY_HOURS = 48
PUT_FALLBACK_DAYS = 14
PUT_MAX_WAIT      = 35

PUT_NO_FETCH = {
    "news.google.com","www.bing.com","bing.com","news.bing.com","google.com","www.google.com",
    "lagazzettadelmezzogiorno.it","www.lagazzettadelmezzogiorno.it",
    "corriere.it","corrieredelmezzogiorno.corriere.it",
}

PUT_RSS = [
    ("PutignanoNews",         "https://www.putignanonews.it/feed/",                                                         1.00),
    ("PutignanoNews-Cronaca", "https://www.putignanonews.it/category/cronaca/feed/",                                         1.00),
    ("PutignanoViva",         "https://www.putignanoviva.it/feed/",                                                          1.00),
    ("LaVoceDiPutignano",     "https://www.lavocediputignano.it/feed/",                                                      1.00),
    ("Informatissimo",        "https://www.informatissimo.net/feed/",                                                        0.97),
    ("Informatissimo-Cronaca","https://www.informatissimo.net/cronaca/feed/",                                                0.97),
    ("Informatissimo-Attual", "https://www.informatissimo.net/attualita/feed/",                                              0.95),
    ("FaxOnline-Putignano",   "https://www.faxonline.it/putignano/feed/",                                                    0.95),
    ("PugliaLive-Putignano",  "https://www.puglialive.net/tag/putignano/feed/",                                              0.93),
    ("NoinotiziePuglia",      "https://www.noinotizie.it/tag/putignano/feed/",                                               0.90),
    ("TeleRama",              "https://www.telerama.it/tag/putignano/feed/",                                                 0.87),
    ("BariToday-Putignano",   "https://www.baritoday.it/rss/tag/putignano.xml",                                              0.85),
    ("CorriereMezzogiorno",   "https://corrieredelmezzogiorno.corriere.it/rss/bari.xml",                                     0.83),
    ("GazzettaMzg-PutNoci",   "https://www.lagazzettadelmezzogiorno.it/rss/tag/putignano-noci.xml",                          0.80),
    ("TRMTV-Cronaca",         "https://www.trmtv.it/news/cronaca/feed/",                                                     0.82),
    ("LaVocePaese-Gioia",     "https://gioia.lavocedelpaese.info/feed/",                                                     0.80),
    ("Buonasera24",           "https://buonasera24.it/feed/",                                                                0.75),
    ("BariToday-Alberobello", "https://www.baritoday.it/rss/tag/alberobello.xml",                                            0.72),
    ("BariToday-Noci",        "https://www.baritoday.it/rss/tag/noci.xml",                                                   0.72),
    ("BariToday-GioiaColle",  "https://www.baritoday.it/rss/tag/gioia-del-colle.xml",                                        0.72),
    ("BariToday-Conversano",  "https://www.baritoday.it/rss/tag/conversano.xml",                                             0.72),
    ("BariToday-Castellana",  "https://www.baritoday.it/rss/tag/castellana-grotte.xml",                                      0.72),
    ("BariToday-Polignano",   "https://www.baritoday.it/rss/tag/polignano-a-mare.xml",                                       0.72),
    ("BariToday-Monopoli",    "https://www.baritoday.it/rss/tag/monopoli.xml",                                               0.72),
    ("GoogleNews-Putignano",  "https://news.google.com/rss/search?q=Putignano+BA&hl=it&gl=IT&ceid=IT:it",                    0.40),
    ("GoogleNews-Alberobello","https://news.google.com/rss/search?q=Alberobello+BA&hl=it&gl=IT&ceid=IT:it",                  0.35),
    ("GoogleNews-Noci",       "https://news.google.com/rss/search?q=Noci+BA+notizie&hl=it&gl=IT&ceid=IT:it",                 0.35),
    ("GoogleNews-Gioia",      "https://news.google.com/rss/search?q=Gioia+del+Colle+notizie&hl=it&gl=IT&ceid=IT:it",         0.35),
    ("GoogleNews-Turi",       "https://news.google.com/rss/search?q=Turi+BA+notizie&hl=it&gl=IT&ceid=IT:it",                 0.33),
    ("GoogleNews-Conversano", "https://news.google.com/rss/search?q=Conversano+notizie&hl=it&gl=IT&ceid=IT:it",              0.33),
    ("GoogleNews-Castellana", "https://news.google.com/rss/search?q=Castellana+Grotte+notizie&hl=it&gl=IT&ceid=IT:it",       0.33),
    ("GoogleNews-Polignano",  "https://news.google.com/rss/search?q=Polignano+a+Mare+notizie&hl=it&gl=IT&ceid=IT:it",        0.33),
    ("GoogleNews-Monopoli",   "https://news.google.com/rss/search?q=Monopoli+BA+notizie&hl=it&gl=IT&ceid=IT:it",             0.33),
]

PUT_SCRAPE = [
    {"name":"Comune Putignano",    "url":"https://www.comune.putignano.ba.it/notizie/",          "weight":1.00,
     "item_sel":"article, .notizia, li.item","title_sel":"h2, h3, .titolo",
     "desc_sel":"p, .testo","link_sel":"a","link_base":"https://www.comune.putignano.ba.it"},
    {"name":"PutignanoViva",       "url":"https://www.putignanoviva.it/",                         "weight":1.00,
     "item_sel":"article, .post","title_sel":"h2, h3, .entry-title",
     "desc_sel":"p, .entry-summary","link_sel":"a","link_base":""},
    {"name":"LaVoceDiPutignano",   "url":"https://www.lavocediputignano.it/",                     "weight":1.00,
     "item_sel":"article, .post","title_sel":"h2, h3",
     "desc_sel":"p","link_sel":"a","link_base":""},
    {"name":"Informatissimo",      "url":"https://www.informatissimo.net/",                       "weight":0.97,
     "item_sel":"article, .post, .item-page","title_sel":"h2, h3, .article-title",
     "desc_sel":"p, .article-intro","link_sel":"a","link_base":"https://www.informatissimo.net"},
    {"name":"BariToday Putignano", "url":"https://www.baritoday.it/tag/putignano/",               "weight":0.90,
     "item_sel":"article, .article-item","title_sel":"h2, h3, .title",
     "desc_sel":"p, .description","link_sel":"a","link_base":"https://www.baritoday.it"},
    {"name":"GazzettaMezzogiorno", "url":"https://www.lagazzettadelmezzogiorno.it/tag/putignano", "weight":0.88,
     "item_sel":"article, .article, .item","title_sel":"h2, h3, .title, .article-title",
     "desc_sel":"p, .description, .summary","link_sel":"a",
     "link_base":"https://www.lagazzettadelmezzogiorno.it"},
    {"name":"TRMTV",               "url":"https://www.trmtv.it/news/cronaca/",                    "weight":0.80,
     "item_sel":"article, .post, .news-item","title_sel":"h2, h3, .title",
     "desc_sel":"p, .excerpt","link_sel":"a","link_base":"https://www.trmtv.it"},
    {"name":"Buonasera24",         "url":"https://buonasera24.it/news/cronaca/",                  "weight":0.75,
     "item_sel":"article, .post, .article-item","title_sel":"h2, h3, .title",
     "desc_sel":"p, .excerpt","link_sel":"a","link_base":"https://buonasera24.it"},
    {"name":"ViviCastellanaGrotte","url":"https://www.vivicastellanagrotte.it/index.php/notizietop","weight":0.65,
     "item_sel":"article, .notizia, li.item, tr","title_sel":"h2, h3, a.contenuto_titolo",
     "desc_sel":"p, .contenuto_intro","link_sel":"a","link_base":"https://www.vivicastellanagrotte.it"},
    {"name":"Comune Alberobello",  "url":"https://www.comune.alberobello.ba.it/notizie/",         "weight":0.80,
     "item_sel":"article, .notizia, li.item","title_sel":"h2, h3",
     "desc_sel":"p","link_sel":"a","link_base":"https://www.comune.alberobello.ba.it"},
    {"name":"Comune Monopoli",     "url":"https://www.comune.monopoli.ba.it/notizie/",            "weight":0.80,
     "item_sel":"article, .notizia, li.item","title_sel":"h2, h3",
     "desc_sel":"p","link_sel":"a","link_base":"https://www.comune.monopoli.ba.it"},
]

COMUNI_ZONA = ["putignano","alberobello","noci","gioia del colle",
               "turi","conversano","castellana grotte","polignano","monopoli"]

PUT_FONTI_DIRETTE = {
    "PutignanoNews","PutignanoNews-Cronaca","PutignanoViva","LaVoceDiPutignano",
    "Informatissimo","Informatissimo-Cronaca","Informatissimo-Attual","FaxOnline-Putignano",
    "Comune Putignano",
}

def is_zona(t):
    tl = t.lower()
    return any(c in tl for c in COMUNI_ZONA)

def componi_frase_put(title, desc, link="", min_car=400, max_car=620):
    t = pulisci_testo(title)
    d = pulisci_testo(pulisci_desc(desc, max_car=max_car))
    if len(d) < min_car - len(t) - 2 and link:
        extra = fetch_article_text(link, max_car=max_car, domini_no_fetch=PUT_NO_FETCH)
        if extra and len(extra) > len(d):
            d = pulisci_testo(pulisci_desc(extra, max_car=max_car))
    if t and d:
        base = d if d.lower().startswith(t[:25].lower()) else (t + ": " + d if d[0].isupper() else t + ", " + d)
    elif t: base = t
    else:   base = d
    if len(base) > max_car:
        for sep in (". ", ", ", "; "):
            pos = base[:max_car].rfind(sep)
            if pos > min_car:
                base = base[:pos]
                break
    base = re.sub(r"\s+", " ", base).strip()
    if base and not base.endswith("."): base += "."
    return normalizza_per_tts(base)

def fetch_scrape_put(src, cutoff):
    if not HAS_REQUESTS: return []
    results = []
    try:
        r = requests.get(src["url"], headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for pos, item in enumerate(soup.select(src["item_sel"])[:20]):
            title_tag = item.select_one(src["title_sel"])
            title_raw = strip_html(title_tag.get_text()) if title_tag else ""
            if not title_raw or len(title_raw) < 10: continue
            desc_tag = item.select_one(src["desc_sel"])
            desc_raw = strip_html(desc_tag.get_text()) if desc_tag else ""
            blob = (title_raw + " " + desc_raw).lower()
            if not is_zona(blob) or is_junk(blob): continue
            link_tag = item.select_one(src["link_sel"])
            link = ""
            if link_tag and link_tag.get("href"):
                href = link_tag["href"]
                link = href if href.startswith("http") else src["link_base"] + href
            results.append({"source": src["name"], "weight": src["weight"], "pos": pos,
                            "dt": None, "title": title_raw.strip(), "desc": desc_raw.strip(),
                            "link": link, "norm": normalize(title_raw)})
    except Exception: pass
    return results

def score_put(item, now):
    s = item["weight"]
    if item.get("dt"):
        age_h = max(0, (now - item["dt"]).total_seconds() / 3600)
        s *= max(0.3, 1 - age_h / (7 * 24))
    s *= 1 + max(0, (10 - item.get("pos", 10)) / 10) * 0.15
    blob = (item["title"] + " " + item["desc"]).lower()
    if "putignano" in blob: s *= 1.30
    if any(kw in blob for kw in ["comune","sindaco","ordinanza","delibera","consiglio","lavori",
                                  "inaugurazione","scuola","ospedale","cantiere","carnevale",
                                  "manifestazione","evento","festival","viabilita","ztl"]):
        s *= 1.12
    return s

def get_notizie_putignano(n=PUT_N_NOTIZIE, min_tts=400):
    now_utc = datetime.now(timezone.utc)
    top = []
    for ore in [PUT_PRIMARY_HOURS, PUT_FALLBACK_DAYS * 24]:
        cutoff = now_utc - timedelta(hours=ore)
        raw = []
        # RSS in parallelo
        with ThreadPoolExecutor(max_workers=8) as ex:
            futures_rss    = {ex.submit(fetch_rss_generic, nm, url, w, cutoff, is_zona): nm
                              for nm, url, w in PUT_RSS}
            futures_scrape = {ex.submit(fetch_scrape_put, src, cutoff): src["name"]
                              for src in PUT_SCRAPE}
            all_futures = {**futures_rss, **futures_scrape}
            done, not_done = wait(all_futures, timeout=PUT_MAX_WAIT)
            for f in done:
                try: raw.extend(f.result())
                except: pass
            for f in not_done: f.cancel()
        # Arricchisci desc corte
        for it in raw:
            if len(it["desc"]) < 320 and it.get("link"):
                extra = fetch_article_text(it["link"], max_car=600, domini_no_fetch=PUT_NO_FETCH)
                if extra and len(extra) > len(it["desc"]): it["desc"] = extra
        top = sorted(deduplica(raw), key=lambda it: score_put(it, now_utc), reverse=True)
        if len(top) >= n: break

    # Garanzia slot 0: fonte diretta Putignano
    if top and top[0]["source"] not in PUT_FONTI_DIRETTE:
        for i, it in enumerate(top[1:], 1):
            if it["source"] in PUT_FONTI_DIRETTE:
                top.insert(0, top.pop(i))
                break

    risultati = []
    for it in top[:n]:
        tts = componi_frase_put(it["title"], it["desc"], it.get("link",""))
        if len(tts) < min_tts and it.get("link",""):
            extra = fetch_article_text(it["link"], max_car=700, domini_no_fetch=PUT_NO_FETCH)
            if extra:
                tts2 = componi_frase_put(it["title"], extra, it.get("link",""))
                if len(tts2) > len(tts): tts = tts2
        risultati.append({"title": it["title"], "desc": it["desc"], "testo_tts": tts,
                           "link": it.get("link",""), "source": it["source"], "dt": it.get("dt")})
    return risultati

# ============================================================
# MODULO CURIOSITÀ  (dati incorporati da 100_curiosità.docx)
# ============================================================

def _pulisci_per_tts(testo: str) -> str:
    t = testo.strip()
    t = re.sub(r'\.\s+([A-Za-zÀ-ÿ])', lambda m: ', ' + m.group(1), t)
    t = re.sub(r'\.{2,}|\u2026', '', t)
    t = t.rstrip('. ')
    t = re.sub(r'\s+', ' ', t).strip()
    if t and not t.endswith('.'): t += '.'
    return t

def get_curiosita() -> str:
    return _pulisci_per_tts(random.choice(CURIOSITA_DB))

# ============================================================
# ASSEMBLAGGIO FINALE  (logica di Putignano.py)
# ============================================================

SALUTI_DA_RIMUOVERE = {"arrivederci a domani","a presto","arrivederci","alla prossima"}

def assembla() -> list:
    """
    Costruisce la lista di righe per Lettura.txt con i marker [T][M]/[F].
    Struttura:
      Intestazione
      Meteo
      Farmacie
      Notizie Italia  (5 notizie, voci alternate F/M)
      Notizie Putignano (3 notizie, voci alternate F/M)
      Curiosità
      Saluto finale
    """
    out = []

    # ---- INTESTAZIONE ----
    out += get_intestazione()

    # ---- METEO ----
    meteo_tts = get_meteo()
    out.append("[T] [M] METEO A PUTIGNANO")
    out.append("")
    out.append(f"[T] [F] {meteo_tts}")
    out.append("")

    # ---- FARMACIE ----
    farm_tts = get_farmacie()
    out.append("[T] [M] FARMACIE DI TURNO")
    out.append("")
    out.append(f"[T] [F] {farm_tts}")
    out.append("")

    # ---- NOTIZIE ITALIA ----
    notizie_it = get_notizie_italia()
    out.append("[T] [M] NOTIZIE DALL'ITALIA")
    out.append("")
    voci = ["[F]", "[M]"]
    for i, n in enumerate(notizie_it):
        out.append(f"[T] {voci[i % 2]} {n['testo_tts']}")
        out.append("")

    # ---- NOTIZIE PUTIGNANO ----
    notizie_put = get_notizie_putignano()
    out.append("[T] [M] NOTIZIE DA PUTIGNANO E D'INTORNI")
    out.append("")
    for i, n in enumerate(notizie_put):
        out.append(f"[T] {voci[i % 2]} {n['testo_tts']}")
        out.append("")

    # ---- CURIOSITÀ ----
    cur_tts = get_curiosita()
    out.append("[T] [M] CURIOSITÀ SU PUTIGNANO")
    out.append("")
    out.append(f"[T] [F] {cur_tts}")
    out.append("")

    # ---- SALUTO FINALE ----
    out.append("[T] [M] A risentirci a presto.")

    # Deduplicazione righe vuote consecutive
    clean = []
    prev_blank = False
    for r in out:
        if r.strip() == "":
            if not prev_blank: clean.append("")
            prev_blank = True
        else:
            clean.append(r)
            prev_blank = False

    return clean

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import shutil
    t_start = time.time()

    righe = assembla()

    # Scrivi Lettura.txt nella root (usato dal fetch della pagina)
    out_path = os.path.join(SCRIPT_DIR, "Lettura.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(righe).strip() + "\n")

    elapsed = time.time() - t_start
    print(f"Lettura.txt pronto in {elapsed:.0f}s")

    # ---- Lancia Podcast.py ----
    podcast_script = os.path.join(SCRIPT_DIR, "Podcast.py")
    if os.path.isfile(podcast_script):
        try:
            result = subprocess.run([sys.executable, podcast_script, "x", "v"], timeout=600)
            if result.returncode != 0:
                print(f"Podcast.py errore (rc={result.returncode})")
        except subprocess.TimeoutExpired:
            print("Podcast.py TIMEOUT (600s)")
        except Exception as ex:
            print(f"Podcast.py: {ex}")
    else:
        print("AVVISO: Podcast.py non trovato")

    # ---- Copia in pod/PodPutignano.mp3 ----
    mp3_path = os.path.join(SCRIPT_DIR, "Lettura.mp3")
    pod_path = os.path.join(POD_DIR, "PodPutignano.mp3")
    if os.path.isfile(mp3_path):
        shutil.copy2(mp3_path, pod_path)
        print(f"PodPutignano.mp3 aggiornato")
        try:
            sistema = platform.system()
            if sistema == "Windows":     os.startfile(mp3_path)
            elif sistema == "Darwin":    subprocess.Popen(["open", mp3_path])
            else:                        subprocess.Popen(["xdg-open", mp3_path])
        except Exception:
            pass
    else:
        print("AVVISO: Lettura.mp3 non trovato")
