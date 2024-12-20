<!DOCTYPE html>
<html lang="it">
<head>

<link rel="apple-touch-icon" href="https://github.com/Sebastiano-Mazzarisi/Test/blob/main/Eventi.png">
<link rel="apple-touch-icon" sizes="180x180" href="https://github.com/Sebastiano-Mazzarisi/Test/blob/main/Eventi.png">

    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Prossimi eventi</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body { 
            font-family: Arial, sans-serif; 
            padding: 20px;
            max-width: 100%;
            overflow-x: hidden;
        }

        h1 { 
            color: #444; 
            margin-bottom: 20px;
            font-size: 1.8em;
        }

        ul { 
            list-style-type: none; 
            padding: 0; 
        }

        li { 
            margin-bottom: 35px;
            padding: 15px;
            border-bottom: 1px solid #eee;
        }

        strong { 
            font-size: 1.3em;
            display: block;
            margin-bottom: 5px;
        }

        /* Colori per i diversi tipi di eventi */
        li:has(+ .tipo-evento:contains("Compleanno")) strong {
            color: #00008B; /* Blu scuro per compleanni */
        }

        li:has(+ span:contains("Onomastico")) strong {
            color: #006400; /* Verde scuro per onomastici */
        }

        li:has(+ .tipo-evento:contains("Anniversario")) strong {
            color: #8B0000; /* Rosso scuro per anniversari */
        }

        .tipo-evento { 
            color: #444;
            display: inline-block;
            margin: 5px 0;
        }

        .data-evento {
            display: block;
            padding-bottom: 10px;
        }

        @media screen and (max-width: 768px) {
            body {
                padding: 15px;
            }

            h1 {
                font-size: 1.5em;
            }

            li {
                padding: 10px 5px;
            }

            strong {
                font-size: 1.2em;
            }
        }

        @media screen and (max-width: 320px) {
            body {
                padding: 10px;
            }

            h1 {
                font-size: 1.3em;
            }
        }
    </style>
    <script>
        function calcolaAnni(dataEvento) {
            const oggi = new Date();
            const [giorno, mese, anno] = dataEvento.split('/').map(Number);
            const dataCompleanno = new Date(oggi.getFullYear(), mese - 1, giorno);
            let anni = oggi.getFullYear() - anno;
            
            if (oggi < dataCompleanno) {
                anni--;
            }
            
            return anni;
        }

        function calcolaGiorniMancanti(dataEvento, tipo) {
            const oggi = new Date();
            const [giorno, mese, anno] = dataEvento.split('/').map(Number);
            
            const evento = new Date(oggi.getFullYear(), mese - 1, giorno);
            
            if (evento < oggi) {
                evento.setFullYear(evento.getFullYear() + 1);
            }
            
            const diffTime = evento - oggi;
            const giorniMancanti = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            return giorniMancanti;
        }

        function aggiornaEventi() {
            const elementi = document.querySelectorAll('.data-evento');
            elementi.forEach(el => {
                const data = el.dataset.date;
                const tipo = el.dataset.type;
                const tipoEvento = el.parentElement.querySelector('.tipo-evento');
                
                const giorniMancanti = calcolaGiorniMancanti(data, tipo);
                el.innerText = `Giorni mancanti: ${giorniMancanti}`;

                if ((tipo === 'Compleanno' || tipo === 'AM') && data.split('/').length === 3) {
                    const anni = calcolaAnni(data);
                    const anniSuccessivi = anni + 1;
                    
                    if (tipo === 'Compleanno') {
                        tipoEvento.innerText = `Compleanno (${anniSuccessivi})`;
                    } else {
                        tipoEvento.innerText = `Anniversario (${anniSuccessivi})`;
                    }
                }
            });
        }

        window.onload = aggiornaEventi;
        setInterval(aggiornaEventi, 24 * 60 * 60 * 1000);
    </script>
</head>
<body>
    <h1>Prossimi eventi</h1>
    <ul>
        <li>
            <strong>AM Rosa e Giovanni</strong><br>
            <span class="tipo-evento">Anniversario</span><br>
            Data: 29/12/2004<br>
            <span class="data-evento" data-date="29/12/2004" data-type="AM">Giorni mancanti: </span>
        </li>




<li>
            <strong>Pricci Angela</strong><br>
            <span class="tipo-evento">Compleanno</span><br>
            Data: 13/01/1957<br>
            <span class="data-evento" data-date="13/01/1957" data-type="Compleanno">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Mazzarisi Nino</strong><br>
            <span>Onomastico</span><br>
            Data: 20/01<br>
            <span class="data-evento" data-date="20/01" data-type="Onomastico">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Mazzarisi Maria Grazia</strong><br>
            <span class="tipo-evento">Compleanno</span><br>
            Data: 21/01/1989<br>
            <span class="data-evento" data-date="21/01/1989" data-type="Compleanno">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Rotondi Nicoletta</strong><br>
            <span class="tipo-evento">Compleanno</span><br>
            Data: 12/02/2019<br>
            <span class="data-evento" data-date="12/02/2019" data-type="Compleanno">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Pricci Gilda</strong><br>
            <span>Onomastico</span><br>
            Data: 13/02<br>
            <span class="data-evento" data-date="13/02" data-type="Onomastico">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Pricci Asia</strong><br>
            <span>Onomastico</span><br>
            Data: 19/02<br>
            <span class="data-evento" data-date="19/02" data-type="Onomastico">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Pricci Tiziana</strong><br>
            <span>Onomastico</span><br>
            Data: 03/03<br>
            <span class="data-evento" data-date="03/03" data-type="Onomastico">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Grilletti Teresa</strong><br>
            <span class="tipo-evento">Compleanno</span><br>
            Data: 05/03/1937<br>
            <span class="data-evento" data-date="05/03/1937" data-type="Compleanno">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Rotondi Gianni</strong><br>
            <span class="tipo-evento">Compleanno</span><br>
            Data: 08/03/1974<br>
            <span class="data-evento" data-date="08/03/1974" data-type="Compleanno">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Pricci Giuseppe</strong><br>
            <span>Onomastico</span><br>
            Data: 19/03<br>
            <span class="data-evento" data-date="19/03" data-type="Onomastico">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Lefemine Francesco</strong><br>
            <span class="tipo-evento">Compleanno</span><br>
            Data: 20/03/2000<br>
            <span class="data-evento" data-date="20/03/2000" data-type="Compleanno">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Lorusso Benny</strong><br>
            <span>Onomastico</span><br>
            Data: 21/03<br>
            <span class="data-evento" data-date="21/03" data-type="Onomastico">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Mazzarisi Teresa</strong><br>
            <span class="tipo-evento">Compleanno</span><br>
            Data: 01/04/1994<br>
            <span class="data-evento" data-date="01/04/1994" data-type="Compleanno">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Dalena Riccardo</strong><br>
            <span>Onomastico</span><br>
            Data: 03/04<br>
            <span class="data-evento" data-date="03/04" data-type="Onomastico">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Lorusso Cinzia</strong><br>
            <span class="tipo-evento">Compleanno</span><br>
            Data: 06/04/1980<br>
            <span class="data-evento" data-date="06/04/1980" data-type="Compleanno">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Chiarappa Cristiano</strong><br>
            <span>Onomastico</span><br>
            Data: 07/04<br>
            <span class="data-evento" data-date="07/04" data-type="Onomastico">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Lepore Genny</strong><br>
            <span>Onomastico</span><br>
            Data: 11/04<br>
            <span class="data-evento" data-date="11/04" data-type="Onomastico">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Pricci Marica</strong><br>
            <span class="tipo-evento">Compleanno</span><br>
            Data: 12/04/1961<br>
            <span class="data-evento" data-date="12/04/1961" data-type="Compleanno">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Dalena Riccardo</strong><br>
            <span class="tipo-evento">Compleanno</span><br>
            Data: 17/04/1973<br>
            <span class="data-evento" data-date="17/04/1973" data-type="Compleanno">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Pricci Maria Antonietta</strong><br>
            <span class="tipo-evento">Compleanno</span><br>
            Data: 20/04/1951<br>
            <span class="data-evento" data-date="20/04/1951" data-type="Compleanno">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Lefemine Flavia</strong><br>
            <span>Onomastico</span><br>
            Data: 07/05<br>
            <span class="data-evento" data-date="07/05" data-type="Onomastico">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Mazzarisi Nino</strong><br>
            <span class="tipo-evento">Compleanno</span><br>
            Data: 07/05/1957<br>
            <span class="data-evento" data-date="07/05/1957" data-type="Compleanno">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Pricci Maria Antonietta</strong><br>
            <span>Onomastico</span><br>
            Data: 23/05<br>
            <span class="data-evento" data-date="23/05" data-type="Onomastico">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Chiarappa Martino</strong><br>
            <span class="tipo-evento">Compleanno</span><br>
            Data: 24/05/1997<br>
            <span class="data-evento" data-date="24/05/1997" data-type="Compleanno">Giorni mancanti: </span>
        </li>




<li>
            <strong>Lefemine Flavia</strong><br>
            <span class="tipo-evento">Compleanno</span><br>
            Data: 16/11/1996<br>
            <span class="data-evento" data-date="16/11/1996" data-type="Compleanno">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Pricci Luigi</strong><br>
            <span class="tipo-evento">Compleanno</span><br>
            Data: 16/11/1933<br>
            <span class="data-evento" data-date="16/11/1933" data-type="Compleanno">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Lorusso Benny</strong><br>
            <span class="tipo-evento">Compleanno</span><br>
            Data: 17/11/1975<br>
            <span class="data-evento" data-date="17/11/1975" data-type="Compleanno">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Chiarappa Saverio</strong><br>
            <span class="tipo-evento">Compleanno</span><br>
            Data: 26/11/1951<br>
            <span class="data-evento" data-date="26/11/1951" data-type="Compleanno">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Lorusso Nina</strong><br>
            <span class="tipo-evento">Compleanno</span><br>
            Data: 29/11/2015<br>
            <span class="data-evento" data-date="29/11/2015" data-type="Compleanno">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>AM Teresa e Luigi</strong><br>
            <span class="tipo-evento">Anniversario</span><br>
            Data: 03/12/1956<br>
            <span class="data-evento" data-date="03/12/1956" data-type="AM">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Chiarappa Saverio</strong><br>
            <span>Onomastico</span><br>
            Data: 03/12<br>
            <span class="data-evento" data-date="03/12" data-type="Onomastico">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Rotondi Nicoletta</strong><br>
            <span>Onomastico</span><br>
            Data: 06/12<br>
            <span class="data-evento" data-date="06/12" data-type="Onomastico">Giorni mancanti: </span>
        </li>
        
        <li>
            <strong>Lorusso Nina</strong><br>
            <span>Onomastico</span><br>
            Data: 15/12<br>
            <span class="data-evento" data-date="15/12" data-type="Onomastico">Giorni mancanti: </span>
        </li>
    </ul>
</body>
</html>


