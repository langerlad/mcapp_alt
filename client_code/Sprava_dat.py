# -------------------------------------------------------
# Modul: Sprava_dat
# -------------------------------------------------------
import anvil.server
import anvil.users
from . import Spravce_stavu

# Pro zpětnou kompatibilitu
def je_prihlasen():
  """
  Zjistí, zda je uživatel přihlášen (zpětně kompatibilní funkce).
  
  Returns:
      objekt uživatele nebo None
  """
  spravce = Spravce_stavu.Spravce_stavu()
  return spravce.nacti_uzivatele()

def logout():
  """
  Odhlásí uživatele (zpětně kompatibilní funkce).
  """
  spravce = Spravce_stavu.Spravce_stavu()
  spravce.odhlasit()