# -------------------------------------------------------
# RowTemplate: Matice_var (řádek pro variantu)
# -------------------------------------------------------
from ._anvil_designer import Matice_varTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class Matice_var(Matice_varTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.label_matice_nazev_varianty.text = self.item['nazev_varianty']
    self.Matice_krit.items = self.item['kriteria']