# client_code/Dashboard_uziv_komp/Analyza_Row/__init__.py
from ._anvil_designer import Analyza_RowTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ... import Navigace, Spravce_stavu, Utils


class Analyza_Row(Analyza_RowTemplate):
    def __init__(self, **properties):
        self.init_components(**properties)
        self.spravce = Spravce_stavu.Spravce_stavu()

    def button_smazat_click(self, **event_args):
        """
        Zpracuje požadavek na smazání analýzy.
        """
        if Utils.zobraz_potvrzovaci_dialog("Opravdu chcete odstranit tuto analýzu?"):
            try:
                # Smazání analýzy na serveru
                anvil.server.call('smaz_analyzu', self.item['id'])
                
                # Pokud se smazala aktivní analýza, vyčistíme stav
                if self.spravce.ziskej_aktivni_analyzu() == self.item['id']:
                    self.spravce.vycisti_data_analyzy()
                
                # Aktualizace seznamu analýz
                self.parent.raise_event('x-refresh')
                
            except Exception as e:
                Utils.zapsat_chybu(f"Chyba při mazání analýzy: {str(e)}")
                alert(f"Chyba při mazání analýzy: {str(e)}")

    def button_upravit_click(self, **event_args):
        """
        Zpracuje požadavek na úpravu analýzy.
        """
        try:
            Utils.zapsat_info(f"Úprava analýzy s ID: {self.item['id']}")
            
            # Vyčistíme předchozí stav před načtením nové analýzy
            self.spravce.vycisti_data_analyzy()
            
            # Nastavíme ID upravované analýzy - toto je vše co potřebujeme
            self.spravce.nastav_aktivni_analyzu(self.item['id'], True)
            
            # Přejdeme na stránku úpravy analýzy
            Navigace.go('uprava_analyzy')
            
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při přípravě úpravy analýzy: {str(e)}")
            alert(f"Chyba při přípravě úpravy analýzy: {str(e)}")

    def button_vypocet_click(self, **event_args):
        """
        Zpracuje požadavek na zobrazení výstupu analýzy.
        Zobrazí dialog pro výběr metody analýzy.
        """
        try:
            # Nastavíme ID aktivní analýzy
            self.spravce.nastav_aktivni_analyzu(self.item['id'], False)
            
            # Zobrazí dialog pro výběr metody analýzy
            self.zobraz_dialog_vyberu_metody()
            
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při přípravě analýzy: {str(e)}")
            alert(f"Chyba při přípravě analýzy: {str(e)}")
            
    def zobraz_dialog_vyberu_metody(self):
        """
        Zobrazí dialog pro výběr metody analýzy.
        """
        try:
            # Definice dostupných metod
            dostupne_metody = [
                ("Simple Additive Weighting (SAW/WSM)", "saw"),
                ("Weighted Sum Model (WSM)", "wsm"),
                ("Weighted Product Model (WPM)", "wpm"),
                ("TOPSIS (Technique for Order of Preference by Similarity to Ideal Solution)", "topsis"),
                ("ELECTRE (Elimination Et Choix Traduisant la Réalité)", "electre"),
                ("MABAC (Multi-Attributive Border Approximation area Comparison)", "mabac")
            ]
            
            # Vytvoření komponenty pro výběr
            dropdown = DropDown(items=[m[0] for m in dostupne_metody])
            dropdown.selected_value = dostupne_metody[0][0]  # Výchozí hodnota
            
            # Vytvoření panelu s komponenty
            panel = FlowPanel()
            panel.add_component(Label(text="Vyberte metodu analýzy:"))
            panel.add_component(dropdown)
            
            # Zobrazení dialogu
            result = alert(
                content=panel,
                title="Výběr metody analýzy",
                large=True,
                dismissible=True,
                buttons=[("Pokračovat", True), ("Zrušit", False)]
            )
            
            if result:  # Pokud uživatel klikl na "Pokračovat"
                # Získání vybrané metody
                vybrany_text = dropdown.selected_value
                vybrana_metoda = next((kod for nazev, kod in dostupne_metody if nazev == vybrany_text), None)
                
                if vybrana_metoda:
                    # Přesměrování na správnou výstupní stránku podle zvolené metody
                    self.presmeruj_na_vystup_metody(vybrana_metoda)
                else:
                    alert("Nebyla vybrána žádná metoda.")
            
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při zobrazení dialogu pro výběr metody: {str(e)}")
            alert(f"Chyba při výběru metody: {str(e)}")
            
    def presmeruj_na_vystup_metody(self, metoda_kod):
        """
        Přesměruje na stránku s výstupem podle zvolené metody.
        
        Args:
            metoda_kod: Kód zvolené metody (např. 'saw', 'wpm', atd.)
        """
        try:
            analyza_id = self.item['id']
            
            # Přesměrování podle metody
            if metoda_kod == "saw":
                Navigace.go('vystup_saw', analyza_id=analyza_id)
            elif metoda_kod == "wsm":
                Navigace.go('vystup_wsm', analyza_id=analyza_id)
            elif metoda_kod == "wpm":
                Navigace.go('vystup_wpm', analyza_id=analyza_id)
            elif metoda_kod == "topsis":
                Navigace.go('vystup_topsis', analyza_id=analyza_id)
            elif metoda_kod == "electre":
                Navigace.go('vystup_electre', analyza_id=analyza_id)
            elif metoda_kod == "mabac":
                Navigace.go('vystup_mabac', analyza_id=analyza_id)
            else:
                alert(f"Metoda '{metoda_kod}' ještě není implementována")
                
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při přechodu na výstup metody {metoda_kod}: {str(e)}")
            alert(f"Chyba při zobrazení výstupu analýzy: {str(e)}")