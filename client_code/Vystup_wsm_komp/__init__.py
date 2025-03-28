from ._anvil_designer import Vystup_wsm_kompTemplate
from anvil import *
import plotly.graph_objects as go
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users
from .. import Spravce_stavu, Utils, Vypocty


class Vystup_wsm_komp(Vystup_wsm_kompTemplate):
    """
    Formulář pro zobrazení výsledků WSM analýzy (Weighted Sum Model).
    Vylepšená verze původního SAW formuláře s detailnějšími výpočty.
    """
    def __init__(self, analyza_id=None, **properties):
        self.init_components(**properties)
        # Inicializace správce stavu
        self.spravce = Spravce_stavu.Spravce_stavu()
        
        # Použijeme ID z parametrů nebo z aktivní analýzy ve správci
        self.analyza_id = analyza_id or self.spravce.ziskej_aktivni_analyzu()
        
        # Aktualizace nadpisu - WSM (Weighted Sum Model) je totožný s SAW
        if hasattr(self, 'headline_1'):
            self.headline_1.text = "Analýza metodou WSM (Weighted Sum Model)"
        
    def form_show(self, **event_args):
        """Načte a zobrazí data analýzy při zobrazení formuláře."""
        if not self.analyza_id:
            self._zobraz_prazdny_formular()
            return
            
        try:
            Utils.zapsat_info(f"Načítám data analýzy ID: {self.analyza_id}")
            
            # Jediné volání serveru - získání dat analýzy
            analyza_data = anvil.server.call('nacti_kompletni_analyzu', self.analyza_id)
            
            # Uložení dat do správce stavu pro případné další použití
            self.spravce.uloz_data_analyzy(analyza_data['analyza'])
            self.spravce.uloz_kriteria(analyza_data['kriteria'])
            self.spravce.uloz_varianty(analyza_data['varianty'])
            self.spravce.uloz_hodnoty(analyza_data['hodnoty'])
            
            # Zobrazení výsledků
            self._zobraz_kompletni_analyzu(analyza_data)
            
            Utils.zapsat_info("Výsledky WSM analýzy úspěšně zobrazeny")
            
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při načítání analýzy: {str(e)}")
            alert(f"Chyba při načítání analýzy: {str(e)}")

    def _zobraz_prazdny_formular(self):
        """Zobrazí prázdný formulář s informací o chybějících datech."""
        Utils.zapsat_info("Zobrazuji prázdný formulář WSM - chybí ID analýzy")
        self.rich_text_vstupni_data.content = "Nepřišlo žádné ID analýzy."
        self.rich_text_normalizace.content = "Není co počítat."
        self.rich_text_vysledek.content = "Není co počítat."
        self.plot_wsm_vysledek.visible = False

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
            # Využití sdílených funkcí z modulu vypocty
            matice, typy_kriterii, varianty, kriteria = Vypocty.vytvor_hodnoty_matici(analyza_data)
            
            # Získání vah
            vahy = [float(k['vaha']) for k in analyza_data['kriteria']]
            
            # Normalizace matice
            norm_vysledky = Vypocty.normalizuj_matici_minmax(matice, typy_kriterii, varianty, kriteria)
            
            # Výpočet vážených hodnot (nová verze)
            vazene_matice = Vypocty.vypocitej_vazene_hodnoty(
                norm_vysledky['normalizovana_matice'], 
                vahy
            )
            
            # Výpočet WSM výsledků
            wsm_vysledky = Vypocty.wsm_vypocet(
                norm_vysledky['normalizovana_matice'], 
                vahy, 
                varianty
            )
            
            # Zobrazení výsledků
            self._zobraz_normalizaci(norm_vysledky, vazene_matice, vahy)
            self._zobraz_vysledky(wsm_vysledky)
            self._zobraz_citlivostni_analyzu()
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při výpočtu WSM výsledků: {str(e)}")
            self.rich_text_normalizace.content = f"Chyba při výpočtu: {str(e)}"
            self.rich_text_vysledek.content = f"Chyba při výpočtu: {str(e)}"
            self.plot_wsm_vysledek.visible = False
            if hasattr(self, 'rich_text_citlivost'):
                self.rich_text_citlivost.visible = False

    def _zobraz_vstupni_data(self, analyza_data):
        """Zobrazí vstupní data analýzy v přehledné formě."""
        try:
            md = f"""
### {analyza_data['analyza']['nazev']}

#### Základní informace
- Metoda: WSM (Weighted Sum Model)
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

    def _zobraz_normalizaci(self, norm_vysledky, vazene_matice, vahy):
        """
        Zobrazí normalizovanou matici a vážené hodnoty.
        
        Args:
            norm_vysledky: Výsledky normalizace
            vazene_matice: 2D list vážených hodnot
            vahy: List vah kritérií
        """
        try:
            # Uloží hodnoty pro použití v grafu skladby
            self._posledni_normalizacni_vysledky = norm_vysledky
            self._posledni_vazene_matice = vazene_matice
            self._posledni_vahy = vahy
            
            md = "### Normalizace hodnot metodou Min-Max\n\n"
            
            # Normalizační tabulka
            md += "#### Normalizovaná matice\n"
            md += "| Varianta / Krit. | " + " | ".join(norm_vysledky['nazvy_kriterii']) + " |\n"
            md += "|" + "-|"*(len(norm_vysledky['nazvy_kriterii'])+1) + "\n"
            
            for i, var_name in enumerate(norm_vysledky['nazvy_variant']):
                md += f"| {var_name} |"
                for j in range(len(norm_vysledky['nazvy_kriterii'])):
                    md += f" {norm_vysledky['normalizovana_matice'][i][j]:.3f} |"
                md += "\n"

            # Vysvětlení normalizace
            md += """
#### Princip metody Min-Max normalizace:

Pro **Maximalizační kritéria** (čím více, tím lépe):
- Normalizovaná hodnota = (hodnota - minimum) / (maximum - minimum)
- Nejlepší hodnota = 1 (maximum)
- Nejhorší hodnota = 0 (minimum)

Pro **Minimalizační kritéria** (čím méně, tím lépe):
- Normalizovaná hodnota = (maximum - hodnota) / (maximum - minimum)
- Nejlepší hodnota = 1 (minimum)
- Nejhorší hodnota = 0 (maximum)

Kde:
- minimum = nejmenší hodnota v daném kritériu
- maximum = největší hodnota v daném kritériu
"""
            
            # Tabulka vah
            md += "\n#### Váhy kritérií\n"
            md += "| Kritérium | " + " | ".join(norm_vysledky['nazvy_kriterii']) + " |\n"
            md += "|" + "-|"*(len(norm_vysledky['nazvy_kriterii'])+1) + "\n"
            md += "| Váha | " + " | ".join([f"{v:.3f}" for v in vahy]) + " |\n"
            
            # Tabulka vážených hodnot
            md += "\n#### Vážené hodnoty (normalizované hodnoty × váhy)\n"
            md += "| Varianta / Krit. | " + " | ".join(norm_vysledky['nazvy_kriterii']) + " | Součet |\n"
            md += "|" + "-|"*(len(norm_vysledky['nazvy_kriterii'])+2) + "\n"
            
            for i, var_name in enumerate(norm_vysledky['nazvy_variant']):
                md += f"| {var_name} |"
                sum_val = 0
                for j in range(len(norm_vysledky['nazvy_kriterii'])):
                    val = vazene_matice[i][j]
                    sum_val += val
                    md += f" {val:.3f} |"
                md += f" {sum_val:.3f} |\n"
            
            # Interpretace vážených hodnot
            md += """
#### Interpretace vážených hodnot:

1. Pro každé kritérium je normalizovaná hodnota vynásobena příslušnou vahou.
2. Vážené hodnoty ukazují, jak jednotlivé kritérium přispívá ke konečnému hodnocení varianty.
3. **Součet vážených hodnot** představuje konečné skóre varianty a slouží pro určení pořadí variant.
4. Čím vyšší je skóre, tím lépe varianta splňuje požadavky definované kritérii a jejich vahami.
"""
            
            self.rich_text_normalizace.content = md
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při zobrazování normalizace: {str(e)}")
            self.rich_text_normalizace.content = f"Chyba při zobrazování normalizace: {str(e)}"

    def _zobraz_vysledky(self, wsm_vysledky):
        """
        Zobrazí finální výsledky WSM analýzy.
        
        Args:
            wsm_vysledky: Výsledky WSM analýzy
        """
        try:
            md = "### Výsledky WSM analýzy (Weighted Sum Model)\n\n"
            
            # Tabulka výsledků
            md += "#### Pořadí variant\n"
            md += "| Pořadí | Varianta | Skóre | % z maxima |\n"
            md += "|---------|----------|--------|------------|\n"
            
            max_skore = wsm_vysledky['nejlepsi_skore']
            
            for varianta, poradi, skore in wsm_vysledky['results']:
                procento = (skore / max_skore) * 100 if max_skore > 0 else 0
                md += f"| {poradi}. | {varianta} | {skore:.3f} | {procento:.1f}% |\n"

            # Shrnutí výsledků
            md += f"""
#### Shrnutí výsledků

- **Nejlepší varianta:** {wsm_vysledky['nejlepsi_varianta']} (skóre: {wsm_vysledky['nejlepsi_skore']:.3f})
- **Nejhorší varianta:** {wsm_vysledky['nejhorsi_varianta']} (skóre: {wsm_vysledky['nejhorsi_skore']:.3f})
- **Rozdíl nejlepší-nejhorší:** {wsm_vysledky['rozdil_skore']:.3f}
- **Poměr nejhorší/nejlepší:** {(wsm_vysledky['nejhorsi_skore'] / wsm_vysledky['nejlepsi_skore'] * 100):.1f}% z maxima

#### O metodě WSM (Weighted Sum Model)

WSM, také známý jako Simple Additive Weighting (SAW), je jedna z nejjednodušších a nejpoužívanějších metod vícekriteriálního rozhodování.

**Princip metody:**
1. Normalizace hodnot do intervalu [0,1] pomocí metody Min-Max
2. Vynásobení normalizovaných hodnot vahami kritérií
3. Sečtení vážených hodnot pro každou variantu
4. Seřazení variant podle celkového skóre (vyšší je lepší)

**Výhody metody:**
- Jednoduchá a intuitivní
- Transparentní výpočty a výsledky
- Snadná interpretace

**Omezení metody:**
- Předpokládá lineární užitek
- Není vhodná pro silně konfliktní kritéria
- Méně robustní vůči extrémním hodnotám než některé pokročilejší metody

**Kdy použít WSM:**
- Pro rychlé a přehledné rozhodnutí
- Když jsou kritéria vzájemně nezávislá
- Pro situace s jednoduchou strukturou preferencí
"""
            self.rich_text_vysledek.content = md

            # Přidání základního grafu skóre
            self.plot_wsm_vysledek.figure = self._vytvor_graf_vysledku(wsm_vysledky)
            self.plot_wsm_vysledek.visible = True

            # Přidání grafu skladby skóre 
            if hasattr(self, 'plot_wsm_skladba'):
                norm_vysledky = self._posledni_normalizacni_vysledky  #
                vazene_matice = self._posledni_vazene_matice  
                vahy = self._posledni_vahy  
                
                self.plot_wsm_skladba.figure = self._vytvor_graf_skladby_skore(
                    norm_vysledky, vazene_matice, vahy)
                self.plot_wsm_skladba.visible = True
            
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při zobrazování výsledků: {str(e)}")
            self.rich_text_vysledek.content = f"Chyba při zobrazování výsledků: {str(e)}"
            self.plot_wsm_vysledek.visible = False

    def _vytvor_graf_vysledku(self, wsm_vysledky):
        """
        Vytvoří sloupcový graf výsledků pomocí Plotly.
        
        Args:
            wsm_vysledky: Slovník s výsledky WSM analýzy
        
        Returns:
            dict: Plotly figure configuration
        """
        try:
            # Příprava dat pro graf
            varianty = []
            skore = []
            colors = []  # Barvy pro sloupce
            
            # Seřazení dat podle skóre (sestupně)
            for varianta, _, hodnota in wsm_vysledky['results']:
                varianty.append(varianta)
                skore.append(hodnota)
                # Nejlepší varianta bude mít zelenou, nejhorší červenou
                if varianta == wsm_vysledky['nejlepsi_varianta']:
                    colors.append('#2ecc71')  # zelená
                elif varianta == wsm_vysledky['nejhorsi_varianta']:
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
                    'title': 'Celkové skóre variant (WSM)',
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

    def _vytvor_graf_skladby_skore(self, norm_vysledky, vazene_matice, vahy):
        """
        Vytvoří skládaný sloupcový graf zobrazující příspěvek jednotlivých kritérií k celkovému skóre.
        
        Args:
            norm_vysledky: Výsledky normalizace
            vazene_matice: 2D list vážených hodnot
            vahy: List vah kritérií
        
        Returns:
            dict: Plotly figure configuration
        """
        try:
            varianty = norm_vysledky['nazvy_variant']
            kriteria = norm_vysledky['nazvy_kriterii']
            
            # Vytvoření datových sérií pro každé kritérium
            data = []
            
            # Pro každé kritérium vytvoříme jednu sérii dat
            for j, kriterium in enumerate(kriteria):
                hodnoty_kriteria = [vazene_matice[i][j] for i in range(len(varianty))]
                
                data.append({
                    'type': 'bar',
                    'name': kriterium,
                    'x': varianty,
                    'y': hodnoty_kriteria,
                    'text': [f'{h:.3f}' for h in hodnoty_kriteria],
                    'textposition': 'inside',
                })
                
            # Vytvoření grafu
            fig = {
                'data': data,
                'layout': {
                    'title': 'Příspěvek jednotlivých kritérií k celkovému skóre',
                    'barmode': 'stack',  # Skládaný sloupcový graf
                    'xaxis': {
                        'title': 'Varianty',
                        'tickangle': -45 if len(varianty) > 4 else 0
                    },
                    'yaxis': {
                        'title': 'Skóre',
                    },
                    'showlegend': True,
                    'legend': {
                        'title': 'Kritéria',
                        'orientation': 'h',  # Horizontální legenda
                        'y': -0.2,  # Umístění pod grafem
                        'x': 0.5,
                        'xanchor': 'center'
                    },
                    'margin': {'t': 50, 'b': 150}  # Větší spodní okraj pro legendu
                }
            }
            
            return fig
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při vytváření grafu složení skóre: {str(e)}")
            # Vrátíme prázdný graf
            return {
                'data': [],
                'layout': {
                    'title': 'Chyba při vytváření grafu složení skóre'
                }
            }

    def _zobraz_citlivostni_analyzu(self):
        """
        Zobrazí analýzu citlivosti včetně textu a grafů.
        """
        try:
            # Kontrola, zda existují potřebné komponenty
            if not hasattr(self, 'rich_text_citlivost') or not hasattr(self, 'plot_citlivost_skore') or not hasattr(self, 'plot_citlivost_poradi'):
                Utils.zapsat_info("Komponenty pro citlivostní analýzu nejsou k dispozici")
                return
            
            # Připravíme popis analýzy citlivosti
            citlivost_md = """
### Analýza citlivosti vah kritérií

Analýza citlivosti umožňuje posoudit, jak změna váhy vybraného kritéria ovlivní celkové hodnocení variant. 
V grafech níže je znázorněno, jak by se změnilo celkové skóre a pořadí variant při různých vahách prvního kritéria. 
Ostatní váhy jsou vždy proporcionálně upraveny, aby součet všech vah zůstal roven 1.

**Interpretace analýzy citlivosti:**
- Pokud jsou křivky variant blízko u sebe nebo se protínají, značí to, že výsledky jsou citlivé na malé změny ve vahách.
- Pokud jsou křivky variant vzájemně vzdálené bez protnutí, výsledek je robustní a méně citlivý na změny vah.
- Místa, kde se křivky protínají, odpovídají hodnotám vah, při kterých dochází ke změně pořadí variant.

**Praktické využití:** Pomocí analýzy citlivosti můžete identifikovat, jak by se výsledek změnil, pokud byste některému kritériu přikládali větší nebo menší důležitost.
"""
            self.rich_text_citlivost.content = citlivost_md
            
            # Získáme potřebná data pro výpočet
            norm_matice = self._posledni_normalizacni_vysledky['normalizovana_matice']
            varianty = self._posledni_normalizacni_vysledky['nazvy_variant']
            kriteria = self._posledni_normalizacni_vysledky['nazvy_kriterii']
            vahy = self._posledni_vahy
            
            # Výpočet analýzy citlivosti pro první kritérium
            analyza_citlivosti = Vypocty.vypocitej_analyzu_citlivosti(
                norm_matice, vahy, varianty, kriteria)
            
            # Vytvoření grafů citlivosti
            self.plot_citlivost_skore.figure = self._vytvor_graf_citlivosti_skore(
                analyza_citlivosti, varianty)
            self.plot_citlivost_skore.visible = True
            
            self.plot_citlivost_poradi.figure = self._vytvor_graf_citlivosti_poradi(
                analyza_citlivosti, varianty)
            self.plot_citlivost_poradi.visible = True
            
            Utils.zapsat_info("Citlivostní analýza úspěšně zobrazena")
            
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při zobrazování analýzy citlivosti: {str(e)}")
            if hasattr(self, 'rich_text_citlivost'):
                self.rich_text_citlivost.content = f"Chyba při zobrazování analýzy citlivosti: {str(e)}"
            if hasattr(self, 'plot_citlivost_skore'):
                self.plot_citlivost_skore.visible = False
            if hasattr(self, 'plot_citlivost_poradi'):
                self.plot_citlivost_poradi.visible = False
  
    def _vytvor_graf_citlivosti_skore(self, analyza_citlivosti, varianty):
        """
        Vytvoří graf analýzy citlivosti pro celkové skóre.
        
        Args:
            analyza_citlivosti: Výsledky analýzy citlivosti
            varianty: Seznam názvů variant
        
        Returns:
            dict: Plotly figure configuration
        """
        try:
            vahy_rozsah = analyza_citlivosti['vahy_rozsah']
            citlivost_skore = analyza_citlivosti['citlivost_skore']
            zvolene_kriterium = analyza_citlivosti['zvolene_kriterium']
            
            # Vytvoření datových sérií pro každou variantu
            data = []
            
            for i, varianta in enumerate(varianty):
                # Pro každou variantu vytvoříme jednu datovou sérii
                data.append({
                    'type': 'scatter',
                    'mode': 'lines+markers',
                    'name': varianta,
                    'x': vahy_rozsah,
                    'y': [citlivost_skore[j][i] for j in range(len(vahy_rozsah))],
                    'marker': {
                        'size': 8
                    }
                })
                
            # Vytvoření grafu
            fig = {
                'data': data,
                'layout': {
                    'title': f'Analýza citlivosti - vliv změny váhy kritéria "{zvolene_kriterium}" na celkové skóre',
                    'xaxis': {
                        'title': f'Váha kritéria {zvolene_kriterium}',
                        'tickformat': '.1f'
                    },
                    'yaxis': {
                        'title': 'Celkové skóre WSM',
                    },
                    'showlegend': True,
                    'legend': {
                        'title': 'Varianty',
                        'orientation': 'v',
                    },
                    'grid': {
                        'rows': 1, 
                        'columns': 1
                    },
                    'margin': {'t': 50, 'b': 80}
                }
            }
            
            return fig
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při vytváření grafu citlivosti skóre: {str(e)}")
            # Vrátíme prázdný graf
            return {
                'data': [],
                'layout': {
                    'title': 'Chyba při vytváření grafu citlivosti skóre'
                }
            }
    
    def _vytvor_graf_citlivosti_poradi(self, analyza_citlivosti, varianty):
        """
        Vytvoří graf analýzy citlivosti pro pořadí variant.
        
        Args:
            analyza_citlivosti: Výsledky analýzy citlivosti
            varianty: Seznam názvů variant
        
        Returns:
            dict: Plotly figure configuration
        """
        try:
            vahy_rozsah = analyza_citlivosti['vahy_rozsah']
            citlivost_poradi = analyza_citlivosti['citlivost_poradi']
            zvolene_kriterium = analyza_citlivosti['zvolene_kriterium']
            
            # Vytvoření datových sérií pro každou variantu
            data = []
            
            for i, varianta in enumerate(varianty):
                # Pro každou variantu vytvoříme jednu datovou sérii
                data.append({
                    'type': 'scatter',
                    'mode': 'lines+markers',
                    'name': varianta,
                    'x': vahy_rozsah,
                    'y': [citlivost_poradi[j][i] for j in range(len(vahy_rozsah))],
                    'marker': {
                        'size': 8
                    }
                })
                
            # Vytvoření grafu
            fig = {
                'data': data,
                'layout': {
                    'title': f'Analýza citlivosti - vliv změny váhy kritéria "{zvolene_kriterium}" na pořadí variant',
                    'xaxis': {
                        'title': f'Váha kritéria {zvolene_kriterium}',
                        'tickformat': '.1f'
                    },
                    'yaxis': {
                        'title': 'Pořadí',
                        'tickmode': 'linear',
                        'tick0': 1,
                        'dtick': 1,
                        'autorange': 'reversed'  # Obrácené pořadí (1 je nahoře)
                    },
                    'showlegend': True,
                    'legend': {
                        'title': 'Varianty',
                        'orientation': 'v',
                    },
                    'grid': {
                        'rows': 1, 
                        'columns': 1
                    },
                    'margin': {'t': 50, 'b': 80}
                }
            }
            
            return fig
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při vytváření grafu citlivosti pořadí: {str(e)}")
            # Vrátíme prázdný graf
            return {
                'data': [],
                'layout': {
                    'title': 'Chyba při vytváření grafu citlivosti pořadí'
                }
            }