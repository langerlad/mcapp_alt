# client_code/Vystup_saw_komp/__init__.py
from ._anvil_designer import Vystup_saw_kompTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users
from .. import Spravce_stavu, Utils, Vypocty, Vizualizace


class Vystup_saw_komp(Vystup_saw_kompTemplate):
    """
    Formulář pro zobrazení výsledků SAW analýzy.
    Zobrazuje kompletní přehled včetně:
    - vstupních dat (kritéria, varianty, hodnotící matice)
    - normalizované matice
    - vážených hodnot
    - finálních výsledků
    Využívá moduly Vypocty.py pro výpočty a Vizualizace.py pro zobrazování.
    """
    def __init__(self, analyza_id=None, metoda=None, **properties):
        self.init_components(**properties)
        # Inicializace správce stavu
        self.spravce = Spravce_stavu.Spravce_stavu()
        
        # Použijeme ID z parametrů nebo z aktivní analýzy ve správci
        self.analyza_id = analyza_id or self.spravce.ziskej_aktivni_analyzu()

        # Uložíme zvolenou metodu
        self.metoda = metoda or "SAW"  # Výchozí metoda je SAW
    
        # Aktualizujeme titulek podle zvolené metody
        self.headline_1.text = f"Analýza metodou {self.metoda}"
        
    def form_show(self, **event_args):
        """Načte a zobrazí data analýzy při zobrazení formuláře."""
        if not self.analyza_id:
            self._zobraz_prazdny_formular()
            return
            
        try:
            Utils.zapsat_info(f"Načítám výsledky analýzy ID: {self.analyza_id}")
            
            # Načtení dat analýzy z JSON struktury
            analyza_data = anvil.server.call('nacti_analyzu', self.analyza_id)
            
            # Zobrazení výsledků
            self._zobraz_kompletni_analyzu(analyza_data)
            
            Utils.zapsat_info("Výsledky analýzy úspěšně zobrazeny")
            
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při načítání analýzy: {str(e)}")
            alert(f"Chyba při načítání analýzy: {str(e)}")

    def _zobraz_prazdny_formular(self):
        """Zobrazí prázdný formulář s informací o chybějících datech."""
        Utils.zapsat_info("Zobrazuji prázdný formulář - chybí ID analýzy")
        # Nastavíme formát na HTML
        self.rich_text_vstupni_data.format = "html"
        self.rich_text_normalizace.format = "html"
        self.rich_text_vysledek.format = "html"
        
        # Zobrazíme chybové zprávy
        error_html = Vizualizace.vytvor_html_karta(
            Vizualizace.vytvor_html_odstavec("Nepřišlo žádné ID analýzy."),
            "Chyba"
        )
        
        self.rich_text_vstupni_data.content = error_html
        self.rich_text_normalizace.content = error_html
        self.rich_text_vysledek.content = error_html
        self.plot_saw_vysledek.visible = False

    def _zobraz_kompletni_analyzu(self, analyza_data):
        """
        Zobrazí kompletní analýzu včetně všech výpočtů.
        
        Args:
            analyza_data: Slovník s kompletními daty analýzy v JSON formátu
        """
        # Zobrazení vstupních dat
        self._zobraz_vstupni_data(analyza_data)
        
        # Provedení výpočtů
        try:
            # Využití modulu Vypocty.py pro zpracování dat a výpočty
            matice, typy_kriterii, varianty, kriteria, vahy = Vypocty.priprav_data_z_json(analyza_data)
            
            # Normalizace matice
            norm_vysledky = Vypocty.normalizuj_matici_minmax(matice, typy_kriterii, varianty, kriteria)
            
            # Výpočet vážených hodnot
            vazene_matice = Vypocty.vypocitej_vazene_hodnoty(norm_vysledky['normalizovana_matice'], vahy)
            
            # Výpočet výsledků SAW metodou
            saw_vysledky = Vypocty.wsm_vypocet(norm_vysledky['normalizovana_matice'], vahy, varianty)
            
            # Pro analýzu citlivosti
            citlivost_data = Vypocty.vypocitej_analyzu_citlivosti(
                norm_vysledky['normalizovana_matice'], 
                vahy, 
                varianty,
                kriteria
            )
            
            # Zobrazení výsledků
            self._zobraz_normalizaci(norm_vysledky, vazene_matice, vahy)
            self._zobraz_vysledky(saw_vysledky, citlivost_data)
            
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při výpočtu výsledků: {str(e)}")
            
            # Použijeme HTML formát pro chybové zprávy
            error_html = Vizualizace.vytvor_html_karta(
                Vizualizace.vytvor_html_odstavec(f"Chyba při výpočtu: {str(e)}"),
                "Chyba ve výpočtu"
            )
            
            self.rich_text_normalizace.format = "html"
            self.rich_text_vysledek.format = "html"
            self.rich_text_normalizace.content = error_html
            self.rich_text_vysledek.content = error_html
            self.plot_saw_vysledek.visible = False

    def _zobraz_vstupni_data(self, analyza_data):
        """Zobrazí vstupní data analýzy v přehledné formě s využitím HTML."""
        try:
            # Nastavení formátu na HTML
            self.rich_text_vstupni_data.format = "html"
            
            # Základní informace
            nazev = analyza_data['nazev']
            popis = analyza_data.get('popis_analyzy', 'Bez popisu')
            
            # Vytvoření hlavičky sekce pomocí modulů Vizualizace
            html = Vizualizace.vytvor_html_nadpis(nazev, 3)
            
            # Základní informace
            zakladni_info = [
                f"<strong>Metoda:</strong> {self.metoda}",
                f"<strong>Popis:</strong> {popis}"
            ]
            html += Vizualizace.vytvor_html_nadpis("Základní informace", 4)
            html += Vizualizace.vytvor_html_seznam(zakladni_info)
            
            # Tabulka kritérií
            kriteria = analyza_data.get('kriteria', {})
            html += Vizualizace.vytvor_html_tabulku_kriterii(
                kriteria,
                "Kritéria analýzy"
            )
            
            # Seznam variant
            varianty = analyza_data.get('varianty', {})
            html += Vizualizace.vytvor_html_tabulku_variant(
                varianty,
                "Varianty analýzy"
            )
            
            # Hodnotící matice
            kriteria_nazvy = list(kriteria.keys())
            varianty_nazvy = list(varianty.keys())
            
            html += Vizualizace.vytvor_html_matici_hodnot(
                varianty_nazvy,
                kriteria_nazvy,
                varianty,
                "Hodnotící matice"
            )
            
            # Nastavení obsahu komponenty
            self.rich_text_vstupni_data.content = html
            
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při zobrazování vstupních dat: {str(e)}")
            self.rich_text_vstupni_data.format = "html"
            self.rich_text_vstupni_data.content = Vizualizace.vytvor_html_karta(
                Vizualizace.vytvor_html_odstavec(f"Chyba při zobrazování vstupních dat: {str(e)}"),
                "Chyba"
            )

    def _zobraz_normalizaci(self, norm_vysledky, vazene_matice, vahy):
        """
        Zobrazí normalizovanou matici a vážené hodnoty s využitím HTML.
        
        Args:
            norm_vysledky: Výsledky normalizace z Vypocty.normalizuj_matici_minmax
            vazene_matice: Výsledky z Vypocty.vypocitej_vazene_hodnoty
            vahy: Seznam vah kritérií
        """
        try:
            # Nastavení formátu na HTML
            self.rich_text_normalizace.format = "html"
            
            # Extrakce dat pro zobrazení
            varianty = norm_vysledky['nazvy_variant']
            kriteria = norm_vysledky['nazvy_kriterii']
            norm_matice = norm_vysledky['normalizovana_matice']
            
            # Vytvoření HTML obsahu
            html = "<div style='font-family: Arial, sans-serif; line-height: 1.6;'>"
            html += Vizualizace.vytvor_html_nadpis("Normalizace hodnot metodou Min-Max", 3)
            
            # Tabulka normalizovaných hodnot pomocí Vizualizace modulu
            html += Vizualizace.vytvor_html_tabulku_hodnot(
                varianty,
                kriteria,
                norm_matice,
                "Normalizovaná matice",
                formatovaci_funkce=lambda x: f"{x:.3f}"
            )
            
            # Vysvětlení min-max normalizace
            html += """
            <div style="margin: 20px 0; padding: 15px; background-color: #f9f9f9; border-left: 4px solid #4CAF50; border-radius: 4px;">
                <h4>Princip metody Min-Max normalizace:</h4>
                
                <p><strong>Pro Maximalizační kritéria</strong> (čím více, tím lépe):</p>
                <ul>
                    <li>Normalizovaná hodnota = (hodnota - minimum) / (maximum - minimum)</li>
                    <li>Nejlepší hodnota = 1 (maximum)</li>
                    <li>Nejhorší hodnota = 0 (minimum)</li>
                </ul>
                
                <p><strong>Pro Minimalizační kritéria</strong> (čím méně, tím lépe):</p>
                <ul>
                    <li>Normalizovaná hodnota = (maximum - hodnota) / (maximum - minimum)</li>
                    <li>Nejlepší hodnota = 1 (minimum)</li>
                    <li>Nejhorší hodnota = 0 (maximum)</li>
                </ul>
                
                <p><strong>Kde:</strong></p>
                <ul>
                    <li>minimum = nejmenší hodnota v daném kritériu</li>
                    <li>maximum = největší hodnota v daném kritériu</li>
                </ul>
            </div>
            """
            
            # Tabulka vážených hodnot
            html += Vizualizace.vytvor_html_tabulku_hodnot(
                varianty,
                kriteria,
                vazene_matice,
                "Vážené hodnoty (normalizované hodnoty × váhy)",
                formatovaci_funkce=lambda x: f"{x:.3f}"
            )
            
            # Interpretace vážených hodnot
            html += """
            <div style="margin: 20px 0; padding: 15px; background-color: #f9f9f9; border-left: 4px solid #3498db; border-radius: 4px;">
                <h4>Interpretace vážených hodnot:</h4>
                <ol>
                    <li>Pro každé kritérium je normalizovaná hodnota vynásobena příslušnou vahou.</li>
                    <li>Vážené hodnoty ukazují, jak jednotlivé kritérium přispívá ke konečnému hodnocení varianty.</li>
                    <li><strong>Součet vážených hodnot</strong> představuje konečné skóre varianty a slouží pro určení pořadí variant.</li>
                    <li>Čím vyšší je skóre, tím lépe varianta splňuje požadavky definované kritérii a jejich vahami.</li>
                </ol>
            </div>
            """
            
            html += "</div>" # Uzavření hlavního div
            
            # Nastavení obsahu komponenty
            self.rich_text_normalizace.content = html
            
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při zobrazování normalizace: {str(e)}")
            self.rich_text_normalizace.format = "html"
            self.rich_text_normalizace.content = Vizualizace.vytvor_html_karta(
                Vizualizace.vytvor_html_odstavec(f"Chyba při zobrazování normalizace: {str(e)}"),
                "Chyba"
            )

    def _zobraz_vysledky(self, saw_vysledky, citlivost_data=None):
        """
        Zobrazí finální výsledky SAW analýzy s využitím HTML.
        
        Args:
            saw_vysledky: Výsledky SAW analýzy z Vypocty.wsm_vypocet
            citlivost_data: Volitelná data z analýzy citlivosti
        """
        try:
            # Nastavení formátu na HTML
            self.rich_text_vysledek.format = "html"
            
            # Vytvoření HTML dokumentu
            html = f"""
            <div style="font-family: Arial, sans-serif; line-height: 1.6;">
                <h3>Výsledky {self.metoda} analýzy</h3>
            """
            
            # Tabulka s výsledky
            html += Vizualizace.vytvor_html_tabulku_vysledku(
                saw_vysledky['results'],
                {0: "Pořadí", 1: "Varianta", 2: "Skóre"},
                "Pořadí variant"
            )
            
            # Shrnutí výsledků
            max_skore = saw_vysledky['nejlepsi_skore']
            procento = (saw_vysledky['nejhorsi_skore'] / max_skore * 100) if max_skore > 0 else 0
            
            html += Vizualizace.vytvor_html_shrnuti_vysledku(
                saw_vysledky['nejlepsi_varianta'],
                saw_vysledky['nejlepsi_skore'],
                saw_vysledky['nejhorsi_varianta'],
                saw_vysledky['nejhorsi_skore'],
                {"Poměr nejhorší/nejlepší": f"{procento:.1f}% z maxima"}
            )
            
            # Informace o metodě
            html += Vizualizace.vytvor_html_shrnuti_metody(
                self.metoda,
                f"{self.metoda} je jedna z nejjednodušších a nejpoužívanějších metod vícekriteriálního rozhodování.",
                [
                    "Jednoduchá a intuitivní metoda",
                    "Transparentní výpočty a výsledky",
                    "Snadná interpretace"
                ],
                [
                    "Předpokládá lineární užitek",
                    "Není vhodná pro silně konfliktní kritéria",
                    "Méně robustní vůči extrémním hodnotám než některé pokročilejší metody"
                ]
            )
            
            # Uzavření HTML dokumentu
            html += "</div>"
            
            # Nastavení obsahu komponenty
            self.rich_text_vysledek.content = html
            
            # Přidání grafu pomocí Vizualizace modulu
            self.plot_saw_vysledek.figure = Vizualizace.vytvor_sloupovy_graf_vysledku(
                saw_vysledky['results'], 
                saw_vysledky['nejlepsi_varianta'], 
                saw_vysledky['nejhorsi_varianta'],
                self.metoda
            )
            self.plot_saw_vysledek.visible = True
            
            # Pokud máme k dispozici analýzu citlivosti, můžeme přidat další grafy
            if citlivost_data and hasattr(self, 'plot_citlivost'):
                self.plot_citlivost.figure = Vizualizace.vytvor_graf_citlivosti_skore(
                    citlivost_data,
                    citlivost_data['nazvy_variant']
                )
                self.plot_citlivost.visible = True
            
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při zobrazování výsledků: {str(e)}")
            self.rich_text_vysledek.format = "html"
            self.rich_text_vysledek.content = Vizualizace.vytvor_html_karta(
                Vizualizace.vytvor_html_odstavec(f"Chyba při zobrazování výsledků: {str(e)}"),
                "Chyba"
            )
            self.plot_saw_vysledek.visible = False