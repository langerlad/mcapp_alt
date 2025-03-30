# client_code/Vystup_saw_html/__init__.py
from ._anvil_designer import Vystup_saw_htmlTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users
from .. import Spravce_stavu, Utils, Vypocty, Vizualizace


class Vystup_saw_html(Vystup_saw_htmlTemplate):
    """
    Formulář pro zobrazení výsledků SAW analýzy s využitím HTML.
    Zobrazuje kompletní přehled analýzy včetně všech výsledků.
    Využívá moduly Vypocty.py pro výpočty a Vizualizace.py pro generování HTML.
    """
    def __init__(self, analyza_id=None, metoda=None, **properties):
        self.init_components(**properties)
        # Inicializace správce stavu
        self.spravce = Spravce_stavu.Spravce_stavu()
        
        # Použijeme ID z parametrů nebo z aktivní analýzy ve správci
        self.analyza_id = analyza_id or self.spravce.ziskej_aktivni_analyzu()

        # Uložíme zvolenou metodu
        self.metoda = metoda or "SAW"  # Výchozí metoda je SAW
    
    def form_show(self, **event_args):
        """Načte a zobrazí data analýzy při zobrazení formuláře."""
        if not self.analyza_id:
            self._zobraz_prazdny_formular()
            return
            
        try:
            Utils.zapsat_info(f"Načítám výsledky analýzy ID: {self.analyza_id} pro HTML výstup")
            
            # Načtení dat analýzy z JSON struktury
            analyza_data = anvil.server.call('nacti_analyzu', self.analyza_id)
            
            # Zobrazení výsledků
            self._zobraz_kompletni_analyzu(analyza_data)
            
            Utils.zapsat_info("Výsledky analýzy úspěšně zobrazeny v HTML")
            
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při načítání analýzy: {str(e)}")
            self._zobraz_chybu(str(e))

    def _zobraz_prazdny_formular(self):
        """Zobrazí prázdný formulář s informací o chybějících datech."""
        self.content_panel.clear()
        
        error_html = HTML(html="""
        <div style="text-align: center; margin-top: 50px; color: #666; font-family: Arial, sans-serif;">
            <h2>Nepřišlo žádné ID analýzy</h2>
            <p>Pro zobrazení výsledků je potřeba vybrat analýzu.</p>
        </div>
        """)
        
        self.content_panel.add_component(error_html)

    def _zobraz_chybu(self, chyba_text):
        """Zobrazí chybovou zprávu."""
        self.content_panel.clear()
        
        error_html = HTML(html=f"""
        <div style="text-align: center; margin-top: 50px; color: #d32f2f; background: #ffebee; 
                    padding: 20px; border-radius: 5px; font-family: Arial, sans-serif;">
            <h2>Chyba při načítání analýzy</h2>
            <p>{chyba_text}</p>
        </div>
        """)
        
        self.content_panel.add_component(error_html)

    def _zobraz_kompletni_analyzu(self, analyza_data):
        """
        Zobrazí kompletní analýzu včetně všech výpočtů.
        
        Args:
            analyza_data: Slovník s kompletními daty analýzy v JSON formátu
        """
        try:
            # Vyčistíme panel obsahu
            self.content_panel.clear()
            
            # Provedení výpočtů pomocí modulu Vypocty
            matice, typy_kriterii, varianty, kriteria, vahy = Vypocty.priprav_data_z_json(analyza_data)
            
            # Normalizace matice
            norm_vysledky = Vypocty.normalizuj_matici_minmax(matice, typy_kriterii, varianty, kriteria)
            
            # Výpočet vážených hodnot
            vazene_matice = Vypocty.vypocitej_vazene_hodnoty(norm_vysledky['normalizovana_matice'], vahy)
            
            # Výpočet výsledků SAW/WSM metodou
            saw_vysledky = Vypocty.wsm_vypocet(norm_vysledky['normalizovana_matice'], vahy, varianty)
            
            # Výpočet analýzy citlivosti
            citlivost_data = Vypocty.vypocitej_analyzu_citlivosti(
                norm_vysledky['normalizovana_matice'], 
                vahy, 
                varianty,
                kriteria
            )
            
            # Vytvoříme HTML komponenty pro jednotlivé sekce a přidáme je do content_panel
            self._pridat_sekci_zakladni_informace(analyza_data)
            self._pridat_sekci_vstupni_data(analyza_data)
            self._pridat_sekci_normalizace(norm_vysledky, vazene_matice, vahy)
            self._pridat_sekci_vysledky(saw_vysledky)
            self._pridat_sekci_grafy(saw_vysledky, vazene_matice, norm_vysledky, citlivost_data)
            
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při zobrazování analýzy: {str(e)}")
            self._zobraz_chybu(f"Chyba při zobrazování výsledků: {str(e)}")

    def _pridat_sekci_zakladni_informace(self, analyza_data):
        """
        Přidá sekci se základními informacemi o analýze.
        
        Args:
            analyza_data: Slovník s daty analýzy
        """
        nazev = analyza_data['nazev']
        popis = analyza_data.get('popis_analyzy', 'Bez popisu')
        
        html_obsah = f"""
        <div style="margin-bottom: 30px; font-family: Arial, sans-serif;">
            <h1 style="color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px;">{nazev}</h1>
            <p style="color: #666; font-size: 16px;">{popis}</p>
            <p><strong>Metoda analýzy:</strong> {self.metoda}</p>
        </div>
        """
        
        html_komponenta = HTML(html=html_obsah)
        self.content_panel.add_component(html_komponenta)

    def _pridat_sekci_vstupni_data(self, analyza_data):
        """
        Přidá sekci se vstupními daty analýzy.
        
        Args:
            analyza_data: Slovník s daty analýzy
        """
        kriteria = analyza_data.get('kriteria', {})
        varianty = analyza_data.get('varianty', {})
        kriteria_nazvy = list(kriteria.keys())
        varianty_nazvy = list(varianty.keys())
        
        # CSS styly pro tuto sekci
        css = """
        <style>
            .data-section {
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                padding: 20px;
                margin-bottom: 30px;
                font-family: Arial, sans-serif;
            }
            .data-section h2 {
                color: #2196F3;
                border-bottom: 2px solid #eee;
                padding-bottom: 10px;
                margin-top: 0;
            }
            .data-section h3 {
                color: #555;
                margin-top: 20px;
            }
            .data-table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }
            .data-table th {
                background-color: #f5f5f5;
                padding: 10px;
                border: 1px solid #ddd;
                font-weight: bold;
                text-align: left;
            }
            .data-table td {
                padding: 8px 10px;
                border: 1px solid #ddd;
            }
            .data-table tr:nth-child(even) {
                background-color: #f9f9f9;
            }
        </style>
        """
        
        # HTML obsah sekce
        html_obsah = f"""
        {css}
        <div class="data-section">
            <h2>Vstupní data</h2>
            
            <h3>Kritéria analýzy</h3>
            <table class="data-table">
                <tr>
                    <th>Název kritéria</th>
                    <th>Typ</th>
                    <th>Váha</th>
                </tr>
        """
        
        # Přidání kritérií do tabulky
        for nazev_krit, krit_data in kriteria.items():
            vaha = float(krit_data['vaha'])
            html_obsah += f"""
                <tr>
                    <td>{nazev_krit}</td>
                    <td>{krit_data['typ'].upper()}</td>
                    <td>{vaha:.3f}</td>
                </tr>
            """
        
        html_obsah += """
            </table>
            
            <h3>Varianty analýzy</h3>
            <table class="data-table">
                <tr>
                    <th>Název varianty</th>
                    <th>Popis</th>
                </tr>
        """
        
        # Přidání variant do tabulky
        for nazev_var, var_data in varianty.items():
            popis = var_data.get('popis_varianty', '')
            html_obsah += f"""
                <tr>
                    <td>{nazev_var}</td>
                    <td>{popis}</td>
                </tr>
            """
        
        html_obsah += """
            </table>
            
            <h3>Hodnotící matice</h3>
            <table class="data-table">
                <tr>
                    <th>Kritérium</th>
        """
        
        # Přidání názvů variant do hlavičky tabulky
        for var_name in varianty_nazvy:
            html_obsah += f"<th>{var_name}</th>"
        
        html_obsah += """
                </tr>
        """
        
        # Přidání hodnot do tabulky
        for nazev_krit in kriteria_nazvy:
            html_obsah += f"<tr><td>{nazev_krit}</td>"
            
            for nazev_var in varianty_nazvy:
                hodnota = varianty[nazev_var].get(nazev_krit, "N/A")
                hodnota_str = f"{hodnota:.2f}" if isinstance(hodnota, (int, float)) else str(hodnota)
                html_obsah += f"<td>{hodnota_str}</td>"
            
            html_obsah += "</tr>"
        
        html_obsah += """
            </table>
        </div>
        """
        
        html_komponenta = HTML(html=html_obsah)
        self.content_panel.add_component(html_komponenta)

    def _pridat_sekci_normalizace(self, norm_vysledky, vazene_matice, vahy):
        """
        Přidá sekci s normalizací a váženými hodnotami.
        
        Args:
            norm_vysledky: Výsledky normalizace
            vazene_matice: Vážené hodnoty
            vahy: Seznam vah
        """
        kriteria = norm_vysledky['nazvy_kriterii']
        varianty = norm_vysledky['nazvy_variant']
        norm_matice = norm_vysledky['normalizovana_matice']
        
        # CSS styly pro tuto sekci
        css = """
        <style>
            .norm-section {
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                padding: 20px;
                margin-bottom: 30px;
                font-family: Arial, sans-serif;
            }
            .norm-section h2 {
                color: #2196F3;
                border-bottom: 2px solid #eee;
                padding-bottom: 10px;
                margin-top: 0;
            }
            .norm-section h3 {
                color: #555;
                margin-top: 20px;
            }
            .info-box {
                background-color: #f0f8ff;
                border-left: 4px solid #2196F3;
                padding: 15px;
                margin: 20px 0;
            }
            .norm-table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }
            .norm-table th {
                background-color: #f5f5f5;
                padding: 10px;
                border: 1px solid #ddd;
                font-weight: bold;
                text-align: center;
            }
            .norm-table td {
                padding: 8px 10px;
                border: 1px solid #ddd;
                text-align: center;
            }
            .norm-table tr:nth-child(even) {
                background-color: #f9f9f9;
            }
            .sum-cell {
                font-weight: bold;
                background-color: #e3f2fd;
            }
        </style>
        """
        
        # HTML obsah sekce
        html_obsah = f"""
        {css}
        <div class="norm-section">
            <h2>Normalizace a výpočet vážených hodnot</h2>
            
            <div class="info-box">
                <h3>Postup výpočtu</h3>
                <p><strong>1. Normalizace hodnot</strong> - převedení všech hodnot na jednotnou škálu [0,1]:</p>
                <ul>
                    <li>Pro MAX kritéria: <code>(hodnota - minimum) / (maximum - minimum)</code></li>
                    <li>Pro MIN kritéria: <code>(maximum - hodnota) / (maximum - minimum)</code></li>
                </ul>
                <p><strong>2. Výpočet vážených hodnot</strong> - vynásobení normalizovaných hodnot vahami kritérií</p>
                <p><strong>3. Celkové skóre</strong> - součet vážených hodnot pro každou variantu</p>
            </div>
            
            <h3>Normalizovaná matice</h3>
            <table class="norm-table">
                <tr>
                    <th>Varianta</th>
        """
        
        # Přidání názvů kritérií do hlavičky tabulky
        for krit in kriteria:
            html_obsah += f"<th>{krit}</th>"
        
        html_obsah += """
                </tr>
        """
        
        # Přidání normalizovaných hodnot do tabulky
        for i, var in enumerate(varianty):
            html_obsah += f"<tr><td>{var}</td>"
            
            for j in range(len(kriteria)):
                hodnota = norm_matice[i][j]
                html_obsah += f"<td>{hodnota:.3f}</td>"
            
            html_obsah += "</tr>"
        
        html_obsah += """
            </table>
            
            <h3>Vážené hodnoty</h3>
            <table class="norm-table">
                <tr>
                    <th>Varianta</th>
        """
        
        # Přidání názvů kritérií do hlavičky tabulky
        for krit in kriteria:
            html_obsah += f"<th>{krit}</th>"
        
        html_obsah += "<th>Součet</th></tr>"
        
        # Přidání vážených hodnot do tabulky
        for i, var in enumerate(varianty):
            html_obsah += f"<tr><td>{var}</td>"
            
            sum_val = 0
            for j in range(len(kriteria)):
                hodnota = vazene_matice[i][j]
                sum_val += hodnota
                html_obsah += f"<td>{hodnota:.3f}</td>"
            
            html_obsah += f"<td class='sum-cell'>{sum_val:.3f}</td></tr>"
        
        html_obsah += """
            </table>
        </div>
        """
        
        html_komponenta = HTML(html=html_obsah)
        self.content_panel.add_component(html_komponenta)

    def _pridat_sekci_vysledky(self, saw_vysledky):
        """
        Přidá sekci s výsledky analýzy.
        
        Args:
            saw_vysledky: Výsledky SAW analýzy
        """
        # CSS styly pro tuto sekci
        css = """
        <style>
            .results-section {
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                padding: 20px;
                margin-bottom: 30px;
                font-family: Arial, sans-serif;
            }
            .results-section h2 {
                color: #2196F3;
                border-bottom: 2px solid #eee;
                padding-bottom: 10px;
                margin-top: 0;
            }
            .results-section h3 {
                color: #555;
                margin-top: 20px;
            }
            .results-table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }
            .results-table th {
                background-color: #f5f5f5;
                padding: 10px;
                border: 1px solid #ddd;
                font-weight: bold;
                text-align: center;
            }
            .results-table td {
                padding: 8px 10px;
                border: 1px solid #ddd;
                text-align: center;
            }
            .best-row {
                background-color: #e8f5e9 !important;
            }
            .worst-row {
                background-color: #ffebee !important;
            }
            .summary-box {
                background-color: #f5f5f5;
                border-left: 4px solid #4CAF50;
                padding: 15px;
                margin: 20px 0;
            }
            .summary-box p {
                margin: 5px 0;
            }
        </style>
        """
        
        # HTML obsah sekce
        html_obsah = f"""
        {css}
        <div class="results-section">
            <h2>Výsledky {self.metoda} analýzy</h2>
            
            <h3>Pořadí variant</h3>
            <table class="results-table">
                <tr>
                    <th>Pořadí</th>
                    <th>Varianta</th>
                    <th>Skóre</th>
                    <th>% z maxima</th>
                </tr>
        """
        
        # Přidání výsledků do tabulky
        max_skore = saw_vysledky['nejlepsi_skore']
        
        for varianta, poradi, skore in saw_vysledky['results']:
            procento = (skore / max_skore) * 100 if max_skore > 0 else 0
            
            # Zvýraznění nejlepší a nejhorší varianty
            row_class = ""
            if varianta == saw_vysledky['nejlepsi_varianta']:
                row_class = "best-row"
            elif varianta == saw_vysledky['nejhorsi_varianta']:
                row_class = "worst-row"
            
            html_obsah += f"""
                <tr class="{row_class}">
                    <td>{poradi}.</td>
                    <td>{varianta}</td>
                    <td>{skore:.3f}</td>
                    <td>{procento:.1f}%</td>
                </tr>
            """
        
        html_obsah += """
            </table>
        """
        
        # Shrnutí výsledků
        html_obsah += f"""
            <div class="summary-box">
                <h3>Shrnutí výsledků</h3>
                <p><strong>Nejlepší varianta:</strong> {saw_vysledky['nejlepsi_varianta']} (skóre: {saw_vysledky['nejlepsi_skore']:.3f})</p>
                <p><strong>Nejhorší varianta:</strong> {saw_vysledky['nejhorsi_varianta']} (skóre: {saw_vysledky['nejhorsi_skore']:.3f})</p>
                <p><strong>Rozdíl nejlepší-nejhorší:</strong> {saw_vysledky['rozdil_skore']:.3f}</p>
                <p><strong>Poměr nejhorší/nejlepší:</strong> {(saw_vysledky['nejhorsi_skore'] / saw_vysledky['nejlepsi_skore'] * 100):.1f}% z maxima</p>
            </div>
            
            <div class="info-box">
                <h3>O metodě {self.metoda}</h3>
                <p>{self.metoda} (Simple Additive Weighting) je jedna z nejjednodušších a nejpoužívanějších metod vícekriteriálního rozhodování.</p>
                
                <h4>Výhody metody:</h4>
                <ul>
                    <li>Jednoduchá a intuitivní</li>
                    <li>Transparentní výpočty a výsledky</li>
                    <li>Snadná interpretace</li>
                </ul>
                
                <h4>Omezení metody:</h4>
                <ul>
                    <li>Předpokládá lineární užitek</li>
                    <li>Není vhodná pro silně konfliktní kritéria</li>
                    <li>Méně robustní vůči extrémním hodnotám než některé pokročilejší metody</li>
                </ul>
            </div>
        </div>
        """
        
        html_komponenta = HTML(html=html_obsah)
        self.content_panel.add_component(html_komponenta)

    def _pridat_sekci_grafy(self, saw_vysledky, vazene_matice, norm_vysledky, citlivost_data):
        """
        Přidá sekci s grafy.
        
        Args:
            saw_vysledky: Výsledky SAW analýzy
            vazene_matice: Vážené hodnoty
            norm_vysledky: Výsledky normalizace
            citlivost_data: Data analýzy citlivosti
        """
        # Přidáme nadpis sekce
        nadpis_html = HTML(html="""
        <div style="margin: 20px 0; font-family: Arial, sans-serif;">
            <h2 style="color: #2196F3; border-bottom: 2px solid #eee; padding-bottom: 10px;">Vizualizace výsledků</h2>
        </div>
        """)
        self.content_panel.add_component(nadpis_html)
        
        # Hlavní graf výsledků
        plot_vysledky = Plot()
        plot_vysledky.figure = Vizualizace.vytvor_sloupovy_graf_vysledku(
            saw_vysledky['results'],
            saw_vysledky['nejlepsi_varianta'],
            saw_vysledky['nejhorsi_varianta'],
            self.metoda
        )
        self.content_panel.add_component(plot_vysledky)
        
        # Přidáme prostor mezi grafy
        spacer = Spacer(height=20)
        self.content_panel.add_component(spacer)
        
        # Nadpis pro skladbu skóre
        nadpis_skladba = HTML(html="""
        <div style="margin: 20px 0; font-family: Arial, sans-serif;">
            <h3 style="color: #555;">Skladba celkového skóre podle kritérií</h3>
        </div>
        """)
        self.content_panel.add_component(nadpis_skladba)
        
        # Graf skladby skóre
        plot_skladba = Plot()
        plot_skladba.figure = Vizualizace.vytvor_skladany_sloupovy_graf(
            norm_vysledky['nazvy_variant'],
            norm_vysledky['nazvy_kriterii'],
            vazene_matice
        )
        self.content_panel.add_component(plot_skladba)
        
        # Přidáme prostor mezi grafy
        spacer2 = Spacer(height=20)
        self.content_panel.add_component(spacer2)
        
        # Nadpis pro analýzu citlivosti
        nadpis_citlivost = HTML(html="""
        <div style="margin: 20px 0; font-family: Arial, sans-serif;">
            <h3 style="color: #555;">Analýza citlivosti vah kritérií</h3>
            <p style="color: #666;">Zobrazuje, jak změna váhy prvního kritéria ovlivní celkové skóre jednotlivých variant.</p>
        </div>
        """)
        self.content_panel.add_component(nadpis_citlivost)
        
        # Graf analýzy citlivosti
        plot_citlivost = Plot()
        plot_citlivost.figure = Vizualizace.vytvor_graf_citlivosti_skore(
            citlivost_data,
            norm_vysledky['nazvy_variant']
        )
        self.content_panel.add_component(plot_citlivost)