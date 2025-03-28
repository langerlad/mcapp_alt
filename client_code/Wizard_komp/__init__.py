# -------------------------------------------------------
# Form: Wizard_komp
# -------------------------------------------------------
from ._anvil_designer import Wizard_kompTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users
from .. import Navigace, Konstanty, Spravce_stavu, Utils


class Wizard_komp(Wizard_kompTemplate):
  def __init__(self, mode=Konstanty.STAV_ANALYZY['NOVY'], **properties):
    self.init_components(**properties)
    
    # Inicializace správce stavu
    self.spravce = Spravce_stavu.Spravce_stavu()
    
    self.mode = mode
    
    # Skrýváme karty (kroky) na začátku
    self.card_krok_2.visible = False
    self.card_krok_3.visible = False
    self.card_krok_4.visible = False
    
    # Získáme ID analýzy ze správce stavu
    self.analyza_id = self.spravce.ziskej_aktivni_analyzu()

    # Event handlery pro repeating panely
    self.repeating_panel_kriteria.set_event_handler('x-refresh', self.nacti_kriteria)
    self.repeating_panel_varianty.set_event_handler('x-refresh', self.nacti_varianty)

    if self.mode == Konstanty.STAV_ANALYZY['UPRAVA']: 
        self.load_existing_analyza()

  def load_existing_analyza(self):
    """Načte existující analýzu pro editaci."""
    try:
        # Pokud nemáme ID analýzy ze správce stavu, zkusíme ho získat ze serveru
        if not self.analyza_id:
            self.analyza_id = anvil.server.call('get_edit_analyza_id')
            if self.analyza_id:
                self.spravce.nastav_aktivni_analyzu(self.analyza_id, True)
        
        if not self.analyza_id:
            raise Exception(Konstanty.ZPRAVY_CHYB['NEPLATNE_ID'])
        
        # Načtení dat přes správce stavu
        if self.spravce.nacti_kompletni_analyzu_ze_serveru(self.analyza_id):
            # Nastavení polí formuláře z dat ve správci stavu
            analyza_data = self.spravce.ziskej_data_analyzy()
            self.text_box_nazev.text = analyza_data.get('nazev', '')
            self.text_area_popis.text = analyza_data.get('popis', '')
            
            # Zobrazení dat z kritérií a variant
            self.nacti_kriteria()
            self.nacti_varianty()
        else:
            raise Exception("Nepodařilo se načíst data analýzy")
            
    except Exception as e:
        Utils.zapsat_chybu(f"Chyba při načítání analýzy: {str(e)}")
        alert(f"Chyba při načítání analýzy: {str(e)}")
        Navigace.go('domu')
      
  def button_dalsi_click(self, **event_args):
    self.label_chyba.visible = False
    chyba = self.validace_vstupu()
    if chyba:
      self.label_chyba.text = chyba
      self.label_chyba.visible = True
      return

    # Cache analytických dat ve správci stavu
    analyza_data = {
      'nazev': self.text_box_nazev.text,
      'popis': self.text_area_popis.text,
    }
    
    self.spravce.uloz_data_analyzy(analyza_data)

    # Check if we're creating a brand new analysis or going back and forth
    if self.mode == Konstanty.STAV_ANALYZY['NOVY']:
      # Only create a new analysis if we don't already have an ID
      if not self.analyza_id:
        self.analyza_id = anvil.server.call(
          "pridej_analyzu", 
          analyza_data['nazev'],
          analyza_data['popis'], 
        )
        # Aktualizujeme ID analýzy ve správci stavu
        self.spravce.nastav_aktivni_analyzu(self.analyza_id, False)
        Utils.zapsat_info(f"Vytvořena nová analýza s ID: {self.analyza_id}")
      else:
        # If we already have an ID, just update the existing analysis
        anvil.server.call(
          'uprav_analyzu',
          self.analyza_id,
          analyza_data['nazev'],
          analyza_data['popis'],
        )
        Utils.zapsat_info(f"Aktualizována existující analýza s ID: {self.analyza_id}")
    else:
      anvil.server.call(
        'uprav_analyzu',
        self.analyza_id,
        analyza_data['nazev'],
        analyza_data['popis'],
      )
      Utils.zapsat_info(f"Aktualizována editovaná analýza s ID: {self.analyza_id}")

    self.card_krok_1.visible = False
    self.card_krok_2.visible = True

  def validace_vstupu(self):
    if not self.text_box_nazev.text:
      return Konstanty.ZPRAVY_CHYB['NAZEV_PRAZDNY']
    if len(self.text_box_nazev.text) > Konstanty.VALIDACE['MAX_DELKA_NAZEV']:
      return Konstanty.ZPRAVY_CHYB['NAZEV_DLOUHY']
    return None

  def button_pridej_kriterium_click(self, **event_args):
    self.label_chyba_2.visible = False
    chyba_2 = self.validace_pridej_kriterium()
    if chyba_2:
      self.label_chyba_2.text = chyba_2
      self.label_chyba_2.visible = True
      return

    # Získáme aktuální kritéria ze správce stavu
    kriteria = self.spravce.ziskej_kriteria()
    
    # Přidáme nové kritérium
    kriteria.append({
      'nazev_kriteria': self.text_box_nazev_kriteria.text,
      'typ': self.drop_down_typ.selected_value,
      'vaha': self.vaha
    })
    
    # Uložíme aktualizovaná kritéria
    self.spravce.uloz_kriteria(kriteria)

    # Reset vstupních polí
    self.text_box_nazev_kriteria.text = ""
    self.drop_down_typ.selected_value = None
    self.text_box_vaha.text = ""

    self.nacti_kriteria()

  def validace_pridej_kriterium(self):
    if not self.text_box_nazev_kriteria.text:
      return "Zadejte název kritéria."
    if not self.drop_down_typ.selected_value:
      return "Vyberte typ kritéria."
    if not self.text_box_vaha.text:
      return Konstanty.ZPRAVY_CHYB['NEPLATNA_VAHA']
    try:    
      vaha_text = self.text_box_vaha.text.replace(',', '.')
      self.vaha = float(vaha_text)
      if not (0 <= self.vaha <= 1):
        return Konstanty.ZPRAVY_CHYB['NEPLATNA_VAHA']
    except ValueError:
      return Konstanty.ZPRAVY_CHYB['NEPLATNA_VAHA']
    return None

  def nacti_kriteria(self, **event_args):
    # Načtení kritérií ze správce stavu
    kriteria = self.spravce.ziskej_kriteria()
    
    self.repeating_panel_kriteria.items = [
      {
        "nazev_kriteria": k["nazev_kriteria"],
        "typ": k["typ"],
        "vaha": k["vaha"]
      } for k in kriteria
    ]

  def button_dalsi_2_click(self, **event_args):
    kriteria = self.spravce.ziskej_kriteria()
    if not kriteria:
      self.label_chyba_2.text = Konstanty.ZPRAVY_CHYB['MIN_KRITERIA']
      self.label_chyba_2.visible = True
      return

    je_validni, zprava = self.kontrola_souctu_vah()
    if not je_validni:
      self.label_chyba_2.text = zprava
      self.label_chyba_2.visible = True
      return
    
    self.label_chyba_2.visible = False
    self.card_krok_2.visible = False
    self.card_krok_3.visible = True

  def kontrola_souctu_vah(self):
    """Kontroluje, zda součet všech vah kritérií je roven 1"""
    kriteria = self.spravce.ziskej_kriteria()
    soucet_vah = sum(float(k['vaha']) for k in kriteria)
    soucet_vah = round(soucet_vah, 3)  # Pro jistotu zaokrouhlení
    
    if abs(soucet_vah - 1.0) > Konstanty.VALIDACE['TOLERANCE_SOUCTU_VAH']:
      return False, Konstanty.ZPRAVY_CHYB['SUMA_VAH'].format(soucet_vah)
    return True, None

  def button_pridej_variantu_click(self, **event_args):
    self.label_chyba_3.visible = False
    chyba_3 = self.validace_pridej_variantu()
    if chyba_3:
      self.label_chyba_3.text = chyba_3
      self.label_chyba_3.visible = True
      return

    # Získáme varianty ze správce stavu
    varianty = self.spravce.ziskej_varianty()
    
    # Přidáme novou variantu
    varianty.append({
      'nazev_varianty': self.text_box_nazev_varianty.text,
      'popis_varianty': self.text_box_popis_varianty.text
    })
    
    # Uložíme aktualizované varianty
    self.spravce.uloz_varianty(varianty)

    self.text_box_nazev_varianty.text = ""
    self.text_box_popis_varianty.text = ""

    self.nacti_varianty()

  def validace_pridej_variantu(self):
    if not self.text_box_nazev_varianty.text:
      return "Zadejte název varianty."
    return None

  def nacti_varianty(self, **event_args):
    # Načtení variant ze správce stavu
    varianty = self.spravce.ziskej_varianty()
    
    self.repeating_panel_varianty.items = [
      {
        "nazev_varianty": v["nazev_varianty"],
        "popis_varianty": v["popis_varianty"]
      } for v in varianty
    ]

  def button_dalsi_3_click(self, **event_args):
    varianty = self.spravce.ziskej_varianty()
    if not varianty:
      self.label_chyba_3.text = Konstanty.ZPRAVY_CHYB['MIN_VARIANTY']
      self.label_chyba_3.visible = True
      return

    self.card_krok_3.visible = False
    self.card_krok_4.visible = True
    self.zobraz_krok_4()

  def zobraz_krok_4(self, **event_args):
    """Naplní RepeatingPanel (Matice_var) daty pro zadání matice hodnot."""
    varianty = self.spravce.ziskej_varianty()
    kriteria = self.spravce.ziskej_kriteria()
    hodnoty = self.spravce.ziskej_hodnoty()
    
    matice_data = []
    for varianta in varianty:
        kriteria_pro_variantu = []
        for k in kriteria:
            key = f"{varianta['nazev_varianty']}_{k['nazev_kriteria']}"
            hodnota = hodnoty['matice_hodnoty'].get(key, '')
            
            kriteria_pro_variantu.append({
                'nazev_kriteria': k['nazev_kriteria'],
                'id_kriteria': k['nazev_kriteria'],
                'hodnota': hodnota
            })

        matice_data.append({
            'nazev_varianty': varianta['nazev_varianty'],
            'id_varianty': varianta['nazev_varianty'],
            'kriteria': kriteria_pro_variantu
        })

    self.Matice_var.items = matice_data

  def button_ulozit_4_click(self, **event_args):
    """Uloží kompletní analýzu na server, pokud je matice validní."""
    if not self.validuj_matici():
        return
        
    try:
        # Získáme data ze správce stavu
        kriteria = self.spravce.ziskej_kriteria()
        varianty = self.spravce.ziskej_varianty()
        hodnoty = self.spravce.ziskej_hodnoty()
        
        Utils.zapsat_info(f"Ukládám analýzu {self.analyza_id}")
        Utils.zapsat_info(f"Počet kritérií: {len(kriteria)}")
        Utils.zapsat_info(f"Počet variant: {len(varianty)}")
        Utils.zapsat_info(f"Počet hodnot: {len(hodnoty.get('matice_hodnoty', {}))}")
        
        anvil.server.call(
            'uloz_kompletni_analyzu', 
            self.analyza_id,
            kriteria,
            varianty,
            hodnoty
        )
        self.mode = Konstanty.STAV_ANALYZY['ULOZENY']
        alert(Konstanty.ZPRAVY_CHYB['ANALYZA_ULOZENA'])
        
        # Vyčistíme data ve správci stavu
        self.spravce.vycisti_data_analyzy()
        
        Navigace.go('domu')
    except Exception as e:
        error_msg = f"Chyba při ukládání: {str(e)}"
        Utils.zapsat_chybu(error_msg)
        self.label_chyba_4.text = error_msg
        self.label_chyba_4.visible = True

  def validuj_matici(self):
    """Validuje a ukládá hodnoty matice."""
    matrix_values = {'matice_hodnoty': {}}
    errors = []
    
    for var_row in self.Matice_var.get_components():
        for krit_row in var_row.Matice_krit.get_components():
            hodnota_text = krit_row.text_box_matice_hodnota.text
            
            if not hodnota_text:
                errors.append("Všechny hodnoty musí být vyplněny")
                continue
                
            try:
                hodnota_text = hodnota_text.replace(',', '.')
                hodnota = float(hodnota_text)
                krit_row.text_box_matice_hodnota.text = str(hodnota)
                
                key = f"{var_row.item['id_varianty']}_{krit_row.item['id_kriteria']}"
                matrix_values['matice_hodnoty'][key] = hodnota
                
            except ValueError:
                errors.append(
                    Konstanty.ZPRAVY_CHYB['NEPLATNA_HODNOTA'].format(
                        var_row.item['nazev_varianty'],
                        krit_row.item['nazev_kriteria']
                    )
                )

    if errors:
        self.label_chyba_4.text = "\n".join(list(set(errors)))
        self.label_chyba_4.visible = True
        return False

    # Ukládáme validované hodnoty matice do správce stavu
    self.spravce.uloz_hodnoty(matrix_values)
    self.label_chyba_4.visible = False
    return True

  def button_zpet_2_click(self, **event_args):
    # Při návratu z kritérií na první krok
    self.card_krok_1.visible = True
    self.card_krok_2.visible = False

  def button_zpet_3_click(self, **event_args):
    # Při návratu z variant na kritéria
    self.card_krok_2.visible = True
    self.card_krok_3.visible = False

  def button_zpet_4_click(self, **event_args):
    # Při návratu z matice na varianty
    self.card_krok_3.visible = True
    self.card_krok_4.visible = False

  def button_zrusit_click(self, **event_args):
    """Handles the cancel button click."""
    try:
        if self.mode == Konstanty.STAV_ANALYZY['NOVY']:
            if Utils.zobraz_potvrzovaci_dialog(Konstanty.ZPRAVY_CHYB['POTVRZENI_ZRUSENI_NOVE']):
                if self.analyza_id:
                    try:
                        anvil.server.call('smaz_analyzu', self.analyza_id)
                    except Exception as e:
                        Utils.zapsat_chybu(f"Chyba při mazání analýzy: {str(e)}")
                # Vyčistíme data ve správci stavu
                self.spravce.vycisti_data_analyzy()
                Navigace.go('domu')
                
        elif self.mode == Konstanty.STAV_ANALYZY['UPRAVA']:
            if Utils.zobraz_potvrzovaci_dialog(Konstanty.ZPRAVY_CHYB['POTVRZENI_ZRUSENI_UPRAVY']):
                self.mode = Konstanty.STAV_ANALYZY['ULOZENY']  # Prevent deletion prompt
                # Vyčistíme data ve správci stavu
                self.spravce.vycisti_data_analyzy()
                Navigace.go('domu')
                
    except Exception as e:
        Utils.zapsat_chybu(f"Chyba při rušení analýzy: {str(e)}")
        alert(f"Nastala chyba: {str(e)}")
        # I v případě chyby se pokusíme vyčistit stav a přejít na domovskou stránku
        self.spravce.vycisti_data_analyzy()
        Navigace.go('domu')