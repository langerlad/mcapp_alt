# -------------------------------------------------------
# RowTemplate: Matice_krit (řádek pro každé kritérium)
# Upraveno pro novou strukturu dat
# -------------------------------------------------------
from ._anvil_designer import Matice_kritTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .... import Spravce_stavu

class Matice_krit(Matice_kritTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.spravce = Spravce_stavu.Spravce_stavu()
    self.label_matice_nazev_kriteria.text = self.item['nazev_kriteria']
    self.text_box_matice_hodnota.text = str(self.item['hodnota']) if self.item['hodnota'] != '' else ''
    
  def text_box_matice_hodnota_lost_focus(self, **event_args):
    """Handler při opuštění textového pole s hodnotou kritéria."""
    try:
        # Získáme ID varianty z nadřazené komponenty
        var_id = self.parent.parent.item['id_varianty']
        krit_id = self.item['id_kriteria']
        
        hodnota_text = self.text_box_matice_hodnota.text
        if hodnota_text:
            hodnota_text = hodnota_text.replace(',', '.')
            hodnota = float(hodnota_text)
            
            # Uložíme hodnotu do správce stavu
            self.spravce.uloz_hodnotu_varianty(var_id, krit_id, hodnota)
            
            # Aktualizujeme zobrazení
            self.text_box_matice_hodnota.text = str(hodnota)
    except ValueError:
        # Zobrazíme chybu, pokud hodnota není validní číslo
        alert("Hodnota musí být číslo")
        self.text_box_matice_hodnota.focus()