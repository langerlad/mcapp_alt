from ._anvil_designer import Vystup_wsm_kompTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users
from .. import Spravce_stavu, Utils, Vypocty, Vizualizace


class Vystup_wsm_komp(Vystup_wsm_kompTemplate):
    """
    Formulář pro zobrazení výsledků WSM analýzy (Weighted Sum Model).
    Využívá sdílené moduly pro výpočty a vizualizace.
    """
    def __init__(self, analyza_id=None, **properties):
        self.init_components(**properties)
        # Inicializace správce stavu
        self.spravce = Spravce_stavu.Spravce_stavu()
        
        # Použijeme ID z parametrů nebo z aktivní analýzy ve správci
        self.analyza_id = analyza_id or self.spravce.ziskej_aktivni_analyzu()
        
        # Aktualizace nadpisu
        if hasattr(self, 'headline_1'):
            self.headline_1.text = "Analýza metodou WSM (Weighted Sum Model)"
        
    def form_show(self, **event_args):
        """Načte a zobrazí data analýzy při zobrazení formuláře."""
        if not self.analyza_id:
            self._zobraz_prazdny_formular()
            return
            
        try:
            Utils.zapsat_info(f"Načítám data analýzy ID: {self.analyza_id}")
            
            # Načtení dat analýzy z JSON struktury
            analyza_data = anvil.server.call('nacti_analyzu', self.analyza_id)
            
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
            analyza_data: Slovník s daty analýzy v JSON formátu
        """
        # Zobrazení vstupních dat
        self._zobraz_vstupni_data(analyza_data)
        
        # Provedení výpočtů
        try:
            # Využití sdílených funkcí z modulu Vypocty
            matice, typy_kriterii, varianty, kriteria, vahy = Vypocty.priprav_data_z_json(analyza_data)
            
            # Normalizace matice
            norm_vysledky = Vypocty.normalizuj_matici_minmax(matice, typy_kriterii, varianty, kriteria)
            
            # Výpočet vážených hodnot
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
            
            # Uložení dat pro další použití
            self._data_pro_grafy = {
                'norm_vysledky': norm_vysledky,
                'vazene_matice': vazene_matice,
                'vahy': vahy,
                'wsm_vysledky': wsm_vysledky
            }
            
            # Zobrazení výsledků
            self._zobraz_normalizaci(norm_vysledky['normalizovana_matice'], vazene_matice, vahy, norm_vysledky['nazvy_kriterii'], norm_vysledky['nazvy_variant'])
            self._zobraz_vysledky(wsm_vysledky)
            self._zobraz_citlivostni_analyzu(norm_vysledky['normalizovana_matice'], vahy, norm_vysledky['nazvy_variant'], norm_vysledky['nazvy_kriterii'])
            
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
### {analyza_data['nazev']}

#### Základní informace
- Metoda: WSM (Weighted Sum Model)
- Popis: {analyza_data.get('popis_analyzy', 'Bez popisu')}

#### Kritéria
| Název kritéria | Typ | Váha |
|----------------|-----|------|
"""
            # Přidání kritérií
            kriteria = analyza_data.get('kriteria', {})
            for nazev_krit, krit_data in kriteria.items():
                vaha = float(krit_data['vaha'])
                md += f"| {nazev_krit} | {krit_data['typ'].upper()} | {vaha:.3f} |\n"

            # Varianty
            md += "\n#### Varianty\n"
            varianty = analyza_data.get('varianty', {})
            for nazev_var, var_data in varianty.items():
                popis = f" - {var_data.get('popis_varianty', '')}" if var_data.get('popis_varianty') else ""
                md += f"- {nazev_var}{popis}\n"

            # Hodnotící matice
            kriteria_nazvy = list(kriteria.keys())
            varianty_nazvy = list(varianty.keys())
            
            md += "\n#### Hodnotící matice\n"
            md += f"| Kritérium | {' | '.join(varianty_nazvy)} |\n"
            md += f"|{'-' * 10}|{('|'.join('-' * 12 for _ in varianty_nazvy))}|\n"
            
            for nazev_krit in kriteria_nazvy:
                radek = f"| {nazev_krit} |"
                for nazev_var in varianty_nazvy:
                    hodnota = varianty[nazev_var].get(nazev_krit, "N/A")
                    hodnota = f" {hodnota:.2f} |" if isinstance(hodnota, (int, float)) else f" {hodnota} |"
                    radek += hodnota
                md += radek + "\n"

            self.rich_text_vstupni_data.content = md
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při zobrazování vstupních dat: {str(e)}")
            self.rich_text_vstupni_data.content = f"Chyba při zobrazování vstupních dat: {str(e)}"

    def _zobraz_normalizaci(self, norm_matice, vazene_matice, vahy, kriteria, varianty):
        """
        Zobrazí normalizovanou matici a vážené hodnoty.
        
        Args:
            norm_matice: 2D list normalizovaných hodnot
            vazene_matice: 2D list vážených hodnot
            vahy: List vah kritérií
            kriteria: Seznam názvů kritérií
            varianty: Seznam názvů variant
        """
        try:
            md = "### Normalizace hodnot metodou Min-Max\n\n"
            
            # Normalizační tabulka
            md += "#### Normalizovaná matice\n"
            md += "| Varianta / Krit. | " + " | ".join(kriteria) + " |\n"
            md += "|" + "-|"*(len(kriteria)+1) + "\n"
            
            for i, var_name in enumerate(varianty):
                md += f"| {var_name} |"
                for j in range(len(kriteria)):
                    md += f" {norm_matice[i][j]:.3f} |"
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
            md += "| Kritérium | " + " | ".join(kriteria) + " |\n"
            md += "|" + "-|"*(len(kriteria)+1) + "\n"
            md += "| Váha | " + " | ".join([f"{v:.3f}" for v in vahy]) + " |\n"
            
            # Tabulka vážených hodnot
            md += "\n#### Vážené hodnoty (normalizované hodnoty × váhy)\n"
            md += "| Varianta / Krit. | " + " | ".join(kriteria) + " | Součet |\n"
            md += "|" + "-|"*(len(kriteria)+2) + "\n"
            
            for i, var_name in enumerate(varianty):
                md += f"| {var_name} |"
                sum_val = 0
                for j in range(len(kriteria)):
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
"""
            self.rich_text_vysledek.content = md

            # Přidání základního grafu skóre s využitím sdíleného modulu vizualizace
            self.plot_wsm_vysledek.figure = Vizualizace.vytvor_sloupovy_graf_vysledku(
                wsm_vysledky['results'], 
                wsm_vysledky['nejlepsi_varianta'], 
                wsm_vysledky['nejhorsi_varianta'], 
                "WSM"
            )
            self.plot_wsm_vysledek.visible = True

            # Přidání grafu skladby skóre 
            if hasattr(self, 'plot_wsm_skladba'):
                data = self._data_pro_grafy
                self.plot_wsm_skladba.figure = Vizualizace.vytvor_skladany_sloupovy_graf(
                    data['norm_vysledky']['nazvy_variant'],
                    data['norm_vysledky']['nazvy_kriterii'],
                    data['vazene_matice']
                )
                self.plot_wsm_skladba.visible = True
            
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při zobrazování výsledků: {str(e)}")
            self.rich_text_vysledek.content = f"Chyba při zobrazování výsledků: {str(e)}"
            self.plot_wsm_vysledek.visible = False

    def _zobraz_citlivostni_analyzu(self, norm_matice, vahy, varianty, kriteria):
        """
        Zobrazí analýzu citlivosti včetně textu a grafů.
        
        Args:
            norm_matice: 2D list normalizovaných hodnot
            vahy: Seznam vah kritérií
            varianty: Seznam názvů variant
            kriteria: Seznam názvů kritérií
        """
        try:
            # Kontrola, zda existují potřebné komponenty
            if not hasattr(self, 'rich_text_citlivost') or not hasattr(self, 'plot_citlivost_skore'):
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
            
            # Výpočet analýzy citlivosti pro první kritérium s využitím sdílené funkce
            analyza_citlivosti = Vypocty.vypocitej_analyzu_citlivosti(
                norm_matice, 
                vahy, 
                varianty, 
                kriteria
            )
            
            # Zobrazení grafů s využitím sdílených funkcí vizualizace
            if hasattr(self, 'plot_citlivost_skore'):
                self.plot_citlivost_skore.figure = Vizualizace.vytvor_graf_citlivosti_skore(
                    analyza_citlivosti, varianty)
                self.plot_citlivost_skore.visible = True
            
            if hasattr(self, 'plot_citlivost_poradi'):
                self.plot_citlivost_poradi.figure = Vizualizace.vytvor_graf_citlivosti_poradi(
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