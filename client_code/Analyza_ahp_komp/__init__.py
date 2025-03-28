from ._anvil_designer import Analyza_ahp_kompTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users
from .. import Navigace


class Analyza_ahp_komp(Analyza_ahp_kompTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run before the form opens.
    self.nazev = None
    self.popis = None
    self.zvolena_metoda = None

    # Definování možností dropdown menu jako tuple ("text", "hodnota" -> tabulka Analyza)
    self.dostupne_metody = (
        ("Simple Additive Weighting (SAW)", "SAW"),
        #("Weighted Product Model (WPM)", "WPM"),
        #("TOPSIS", "TOPSIS"),
        #("VIKOR", "VIKOR"),
        #("PROMETHEE I, II", "PROMETHEE"),
        #("ELECTRE I, II, III", "ELECTRE"),
    )
  
    # Nastavení hodnot dropdown menu (pouze viditelné texty)
    self.drop_down_metoda.items = [metoda[0] for metoda in self.dostupne_metody]
    
  def drop_down_metoda_change(self, **event_args):
    """This method is called when an item is selected"""
    vybrana_metoda_text = self.drop_down_metoda.selected_value
    
    # Získání odpovídající hodnoty z tuple
    vybrana_metoda_hodnota = next((hodnota for text, hodnota in self.dostupne_metody if text == vybrana_metoda_text), None)

    if vybrana_metoda_hodnota:
      print(f"Vybraná metoda: {vybrana_metoda_text} ({vybrana_metoda_hodnota})")      
    else:
        alert("Vyberte platnou možnost.")
    self.zvolena_metoda = vybrana_metoda_hodnota

  def button_dalsi_click(self, **event_args):
    """This method is called when the button Další krok is clicked"""
    self.label_chyba.visible = False
    chyba = self.validace_vstupu()
    if chyba:
      self.label_chyba.text = chyba
      self.label_chyba.visible = True
      return
      
    print("uložené údaje: {} {} {}".format(self.nazev, self.popis, self.zvolena_metoda))
    anvil.server.call('pridej_analyzu', self.nazev, self.popis, self.zvolena_metoda)

  def validace_vstupu(self):
    if not self.drop_down_metoda.selected_value:
      return "Vyberte metodu výpočtu analýzy"

    if not self.text_box_nazev.text:
      return "Zadejte název analýzy"

    self.nazev = self.text_box_nazev.text
    self.popis =self.text_area_popis.text
    
    return None
    