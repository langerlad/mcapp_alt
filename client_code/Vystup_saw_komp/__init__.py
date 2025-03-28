from ._anvil_designer import Vystup_saw_kompTemplate
from anvil import *
import plotly.graph_objects as go
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users
from .. import Spravce_stavu, Utils


class Vystup_saw_komp(Vystup_saw_kompTemplate):
    """
    Formulář pro zobrazení výsledků SAW analýzy.
    Zobrazuje kompletní přehled včetně:
    - vstupních dat (kritéria, varianty, hodnotící matice)
    - normalizované matice
    - vážených hodnot
    - finálních výsledků
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
            
            # Jediné volání serveru - získání dat analýzy
            analyza_data = anvil.server.call('nacti_kompletni_analyzu', self.analyza_id)
            
            # Uložení dat do správce stavu pro případné další použití
            self.spravce.uloz_data_analyzy(analyza_data['analyza'])
            self.spravce.uloz_kriteria(analyza_data['kriteria'])
            self.spravce.uloz_varianty(analyza_data['varianty'])
            self.spravce.uloz_hodnoty(analyza_data['hodnoty'])
            
            # Zobrazení výsledků
            self._zobraz_kompletni_analyzu(analyza_data)
            
            Utils.zapsat_info("Výsledky analýzy úspěšně zobrazeny")
            
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při načítání analýzy: {str(e)}")
            alert(f"Chyba při načítání analýzy: {str(e)}")

    def _zobraz_prazdny_formular(self):
        """Zobrazí prázdný formulář s informací o chybějících datech."""
        Utils.zapsat_info("Zobrazuji prázdný formulář - chybí ID analýzy")
        self.rich_text_vstupni_data.content = "Nepřišlo žádné ID analýzy."
        self.rich_text_normalizace.content = "Není co počítat."
        self.rich_text_vysledek.content = "Není co počítat."
        self.plot_saw_vysledek.visible = False

    def _zobraz_kompletni_analyzu(self, analyza_data):
        """
        Zobrazí kompletní analýzu včetně všech výpočtů.
        
        Args:
            analyza_data: Slovník s kompletními daty analýzy
        """
          
        # Zobrazení vstupních dat
        self._zobraz_vstupni_data(analyza_data)
        
        # Provedení výpočtů
        try:
            norm_vysledky = self._normalizuj_matici(analyza_data)
            vazene_hodnoty = self._vypocitej_vazene_hodnoty(analyza_data, norm_vysledky)
            saw_vysledky = self._vypocitej_saw_vysledky(analyza_data, vazene_hodnoty)
            
            # Zobrazení výsledků
            self._zobraz_normalizaci(norm_vysledky, vazene_hodnoty)
            self._zobraz_vysledky(saw_vysledky)
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při výpočtu výsledků: {str(e)}")
            self.rich_text_normalizace.content = f"Chyba při výpočtu: {str(e)}"
            self.rich_text_vysledek.content = f"Chyba při výpočtu: {str(e)}"
            self.plot_saw_vysledek.visible = False

    def _zobraz_vstupni_data(self, analyza_data):
        """Zobrazí vstupní data analýzy v přehledné formě."""
        try:
            md = f"""
### {analyza_data['analyza']['nazev']}

#### Základní informace
- Metoda: SAW
- Popis: {analyza_data['analyza']['popis'] or 'Bez popisu'}

#### Kritéria
| Název kritéria | Typ | Váha |
|----------------|-----|------|
"""
            # Přidání kritérií
            for k in analyza_data['kriteria']:
                vaha = float(k['vaha'])
                md += f"| {k['nazev_kriteria']} | {k['typ'].upper()} | {vaha:.3f} |\n"

            # Varianty
            md += "\n#### Varianty\n"
            for v in analyza_data['varianty']:
                popis = f" - {v['popis_varianty']}" if v['popis_varianty'] else ""
                md += f"- {v['nazev_varianty']}{popis}\n"

            # Hodnotící matice
            varianty = [v['nazev_varianty'] for v in analyza_data['varianty']]
            kriteria = [k['nazev_kriteria'] for k in analyza_data['kriteria']]
            
            md += "\n#### Hodnotící matice\n"
            md += f"| Kritérium | {' | '.join(varianty)} |\n"
            md += f"|{'-' * 10}|{('|'.join('-' * 12 for _ in varianty))}|\n"
            
            matice = analyza_data['hodnoty']['matice_hodnoty']
            for krit in kriteria:
                radek = f"| {krit} |"
                for var in varianty:
                    klic = f"{var}_{krit}"
                    hodnota = matice.get(klic, "N/A")
                    hodnota = f" {hodnota:.2f} |" if isinstance(hodnota, (int, float)) else f" {hodnota} |"
                    radek += hodnota
                md += radek + "\n"

            self.rich_text_vstupni_data.content = md
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při zobrazování vstupních dat: {str(e)}")
            self.rich_text_vstupni_data.content = f"Chyba při zobrazování vstupních dat: {str(e)}"

    def _zobraz_normalizaci(self, norm_vysledky, vazene_hodnoty):
        """
        Zobrazí normalizovanou matici a vážené hodnoty.
        
        Args:
            norm_vysledky: Výsledky normalizace
            vazene_hodnoty: Vypočtené vážené hodnoty
        """
        try:
            md = "### Normalizace hodnot\n\n"
            
            # Normalizační tabulka
            md += "| Varianta / Krit. | " + " | ".join(norm_vysledky['nazvy_kriterii']) + " |\n"
            md += "|" + "-|"*(len(norm_vysledky['nazvy_kriterii'])+1) + "\n"
            
            for i, var_name in enumerate(norm_vysledky['nazvy_variant']):
                md += f"| {var_name} |"
                for j in range(len(norm_vysledky['nazvy_kriterii'])):
                    md += f" {norm_vysledky['normalizovana_matice'][i][j]:.3f} |"
                md += "\n"

            # Vysvětlení normalizace
            md += self._vytvor_vysvetleni_normalizace()
            
            # Tabulka vážených hodnot
            md += self._vytvor_tabulku_vazenych_hodnot(vazene_hodnoty)
            
            # Vysvětlení vážených hodnot
            md += self._vytvor_vysvetleni_vazenych_hodnot()
            
            self.rich_text_normalizace.content = md
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při zobrazování normalizace: {str(e)}")
            self.rich_text_normalizace.content = f"Chyba při zobrazování normalizace: {str(e)}"

    def _zobraz_vysledky(self, saw_vysledky):
        """
        Zobrazí finální výsledky SAW analýzy.
        
        Args:
            saw_vysledky: Výsledky SAW analýzy
        """
        try:
            md = "### Výsledky SAW analýzy\n\n"
            
            # Tabulka výsledků
            md += "| Pořadí | Varianta | Skóre |\n"
            md += "|---------|----------|--------|\n"
            
            for varianta, poradi, skore in saw_vysledky['results']:
                md += f"| {poradi}. | {varianta} | {skore:.3f} |\n"

            # Shrnutí výsledků
            md += f"""
#### Shrnutí výsledků
- Nejlepší varianta: {saw_vysledky['nejlepsi_varianta']} (skóre: {saw_vysledky['nejlepsi_skore']:.3f})
- Nejhorší varianta: {saw_vysledky['nejhorsi_varianta']} (skóre: {saw_vysledky['nejhorsi_skore']:.3f})
- Rozdíl nejlepší-nejhorší: {saw_vysledky['rozdil_skore']:.3f}

#### Metoda SAW (Simple Additive Weighting)
1. Princip metody
   - Normalizace hodnot do intervalu [0,1]
   - Vynásobení normalizovaných hodnot vahami
   - Sečtení vážených hodnot pro každou variantu

2. Interpretace výsledků
   - Vyšší skóre znamená lepší variantu
   - Výsledek zohledňuje všechna kritéria dle jejich vah
   - Rozdíly ve skóre ukazují relativní kvalitu variant
"""
            self.rich_text_vysledek.content = md

            # Přidání grafu
            self.plot_saw_vysledek.figure = self._vytvor_graf_vysledku(saw_vysledky)
            self.plot_saw_vysledek.visible = True
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při zobrazování výsledků: {str(e)}")
            self.rich_text_vysledek.content = f"Chyba při zobrazování výsledků: {str(e)}"
            self.plot_saw_vysledek.visible = False

    def _normalizuj_matici(self, analyza_data):
        """
        Provede min-max normalizaci hodnot.
        
        Args:
            analyza_data: Slovník obsahující data analýzy
        
        Returns:
            dict: Slovník obsahující normalizovanou matici a metadata
        """
        try:
            varianty = [v['nazev_varianty'] for v in analyza_data['varianty']]
            kriteria = [k['nazev_kriteria'] for k in analyza_data['kriteria']]
            
            # Vytvoření původní matice
            matice = []
            for var in analyza_data['varianty']:
                radek = []
                for krit in analyza_data['kriteria']:
                    klic = f"{var['nazev_varianty']}_{krit['nazev_kriteria']}"
                    hodnota = float(analyza_data['hodnoty']['matice_hodnoty'].get(klic, 0))
                    radek.append(hodnota)
                matice.append(radek)
            
            # Normalizace pomocí min-max pro každý sloupec (kritérium)
            norm_matice = []
            for i in range(len(matice)):
                norm_radek = []
                for j in range(len(matice[0])):
                    sloupec = [row[j] for row in matice]
                    min_val = min(sloupec)
                    max_val = max(sloupec)
                    
                    if max_val == min_val:
                        norm_hodnota = 1.0  # Všechny hodnoty jsou stejné
                    else:
                        # Pro MIN kritéria obrátíme normalizaci
                        if analyza_data['kriteria'][j]['typ'].lower() in ("min", "cost"):
                            norm_hodnota = (max_val - matice[i][j]) / (max_val - min_val)
                        else:
                            norm_hodnota = (matice[i][j] - min_val) / (max_val - min_val)
                    
                    norm_radek.append(norm_hodnota)
                norm_matice.append(norm_radek)
            
            return {
                'nazvy_variant': varianty,
                'nazvy_kriterii': kriteria,
                'normalizovana_matice': norm_matice
            }
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při normalizaci matice: {str(e)}")
            raise

    def _vypocitej_vazene_hodnoty(self, analyza_data, norm_vysledky):
        """
        Vypočítá vážené hodnoty pro všechny varianty a kritéria.
        
        Args:
            analyza_data: Slovník s daty analýzy
            norm_vysledky: Výsledky normalizace
            
        Returns:
            dict: Slovník vážených hodnot pro každou variantu a kritérium
        """
        try:
            vazene_hodnoty = {}
            
            for i, varianta in enumerate(norm_vysledky['nazvy_variant']):
                vazene_hodnoty[varianta] = {}
                for j, kriterium in enumerate(norm_vysledky['nazvy_kriterii']):
                    norm_hodnota = norm_vysledky['normalizovana_matice'][i][j]
                    vaha = float(analyza_data['kriteria'][j]['vaha'])
                    vazene_hodnoty[varianta][kriterium] = norm_hodnota * vaha
            
            return vazene_hodnoty
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při výpočtu vážených hodnot: {str(e)}")
            raise

    def _vypocitej_saw_vysledky(self, analyza_data, vazene_hodnoty):
        """
        Vypočítá finální výsledky SAW analýzy.
        
        Args:
            analyza_data: Slovník s daty analýzy
            vazene_hodnoty: Slovník vážených hodnot
            
        Returns:
            dict: Slovník obsahující seřazené výsledky a statistiky
        """
        try:
            # Výpočet celkového skóre pro každou variantu
            skore = {}
            for varianta, hodnoty in vazene_hodnoty.items():
                skore[varianta] = sum(hodnoty.values())
            
            # Seřazení variant podle skóre (sestupně)
            serazene = sorted(skore.items(), key=lambda x: x[1], reverse=True)
            
            # Vytvoření seznamu výsledků s pořadím
            results = []
            for poradi, (varianta, hodnota) in enumerate(serazene, 1):
                results.append((varianta, poradi, hodnota))
            
            return {
                'results': results,
                'nejlepsi_varianta': results[0][0],
                'nejlepsi_skore': results[0][2],
                'nejhorsi_varianta': results[-1][0],
                'nejhorsi_skore': results[-1][2],
                'rozdil_skore': results[0][2] - results[-1][2]
            }
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při výpočtu SAW výsledků: {str(e)}")
            raise

    def _vytvor_vysvetleni_normalizace(self):
        """Vytvoří text s vysvětlením normalizace."""
        return """

Normalizační matice představuje úpravu původních hodnot na jednotné měřítko pro spravedlivé porovnání. 
V původních datech mohou být různá kritéria v odlišných jednotkách (např. cena v Kč a kvalita v bodech 1-10). 
Normalizací převedeme všechny hodnoty do intervalu [0,1].

#### Postup normalizace:
1. Pro každé kritérium je určen směr optimalizace (MAX/MIN)
2. Aplikuje se Min-Max normalizace:
   - Pro každý sloupec se najde minimum a maximum
   - Hodnoty jsou transformovány podle vzorce: (x - min) / (max - min)
   - Pro MIN kritéria je výsledek odečten od 1
3. Výsledná normalizovaná matice obsahuje hodnoty v intervalu [0,1]
   - 1 reprezentuje nejlepší hodnotu
   - 0 reprezentuje nejhorší hodnotu

"""

    def _vytvor_tabulku_vazenych_hodnot(self, vazene_hodnoty):
        """
        Vytvoří markdown tabulku vážených hodnot.
        
        Args:
            vazene_hodnoty: Slovník vážených hodnot
            
        Returns:
            str: Markdown formátovaná tabulka
        """
        try:
            varianty = list(vazene_hodnoty.keys())
            if not varianty:
                return ""
                
            kriteria = list(vazene_hodnoty[varianty[0]].keys())
            
            md = "\n#### Vážené hodnoty\n\n"
            md += "| Varianta | " + " | ".join(kriteria) + " | Součet |\n"
            md += "|" + "----|"*(len(kriteria)+2) + "\n"
            
            for var in varianty:
                md += f"| {var} |"
                soucet = 0.0
                for krit in kriteria:
                    hodnota = vazene_hodnoty[var].get(krit, 0)
                    soucet += hodnota
                    md += f" {hodnota:.3f} |"
                md += f" {soucet:.3f} |\n"
            return md
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při vytváření tabulky vážených hodnot: {str(e)}")
            return "\nChyba při vytváření tabulky vážených hodnot\n"

    def _vytvor_vysvetleni_vazenych_hodnot(self):
        """Vytvoří text s vysvětlením vážených hodnot."""
        return """

#### Vysvětlení vážených hodnot:

1. Význam výpočtu
   - Vážené hodnoty vznikají násobením normalizovaných hodnot váhami kritérií
   - Zohledňují jak výkonnost varianty, tak důležitost kritéria

2. Váhy kritérií
   - Každému kritériu je přiřazena váha podle jeho důležitosti
   - Součet všech vah je 1
   - Vyšší váha znamená větší vliv na celkový výsledek

3. Interpretace hodnot
   - Vyšší hodnoty znamenají lepší hodnocení v daném kritériu
   - Součet představuje celkové hodnocení varianty
   - Slouží jako základ pro určení pořadí variant

"""

    def _vytvor_vysvetleni_metody(self):
        """Vytvoří text s vysvětlením metody SAW."""
        return """

#### Metoda SAW (Simple Additive Weighting)
1. Princip metody
   - Normalizace hodnot do intervalu [0,1]
   - Vynásobení normalizovaných hodnot vahami
   - Sečtení vážených hodnot pro každou variantu

2. Interpretace výsledků
   - Vyšší skóre znamená lepší variantu
   - Výsledek zohledňuje všechna kritéria dle jejich vah
   - Rozdíly ve skóre ukazují relativní kvalitu variant
"""

    def _vytvor_graf_vysledku(self, saw_vysledky):
        """
        Vytvoří sloupcový graf výsledků pomocí Plotly.
        
        Args:
            saw_vysledky: Slovník s výsledky SAW analýzy
        
        Returns:
            dict: Plotly figure configuration
        """
        try:
            # Příprava dat pro graf
            varianty = []
            skore = []
            colors = []  # Barvy pro sloupce
            
            # Seřazení dat podle skóre (sestupně)
            for varianta, _, hodnota in saw_vysledky['results']:
                varianty.append(varianta)
                skore.append(hodnota)
                # Nejlepší varianta bude mít zelenou, nejhorší červenou
                if varianta == saw_vysledky['nejlepsi_varianta']:
                    colors.append('#2ecc71')  # zelená
                elif varianta == saw_vysledky['nejhorsi_varianta']:
                    colors.append('#e74c3c')  # červená
                else:
                    colors.append('#3498db')  # modrá
          
            # Vytvoření grafu
            fig = {
                'data': [{
                    'type': 'bar',
                    'x': varianty,
                    'y': skore,
                    'marker': {
                        'color': colors
                    },
                    'text': [f'{s:.3f}' for s in skore],  # Zobrazení hodnot nad sloupci
                    'textposition': 'auto',
                }],
                'layout': {
                    'title': 'Celkové skóre variant',
                    'xaxis': {
                        'title': 'Varianty',
                        'tickangle': -45 if len(varianty) > 4 else 0  # Natočení popisků pro lepší čitelnost
                    },
                    'yaxis': {
                        'title': 'Skóre',
                        'range': [0, max(skore) * 1.1]  # Trochu místa nad sloupci pro hodnoty
                    },
                    'showlegend': False,
                    'margin': {'t': 50, 'b': 100}  # Větší okraje pro popisky
                }
            }
            
            return fig
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při vytváření grafu: {str(e)}")
            # Vrátíme prázdný graf
            return {
                'data': [],
                'layout': {
                    'title': 'Chyba při vytváření grafu'
                }
            }