# -------------------------------------------------------
# Form: Pridej_uzivatele_form
# -------------------------------------------------------
from ._anvil_designer import Pridej_uzivatele_formTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class Pridej_uzivatele_form(Pridej_uzivatele_formTemplate):
    def __init__(self, **properties):
        self.init_components(**properties)
        self.text_box_email.text = ""
        self.text_box_heslo.text = ""
        self.check_box_admin.checked = False
        self.label_chyba.visible = False
        
    def validuj_form(self):
        """Validuje formulář pro přidání uživatele"""
        email = self.text_box_email.text.strip()
        heslo = self.text_box_heslo.text
        
        # Validace emailu
        if not email:
            self.label_chyba.text = "Email je povinný"
            self.label_chyba.visible = True
            return False
            
        if '@' not in email:
            self.label_chyba.text = "Zadejte platný email"
            self.label_chyba.visible = True
            return False
        
        # Validace hesla
        if not heslo:
            self.label_chyba.text = "Heslo je povinné"
            self.label_chyba.visible = True
            return False
            
        if len(heslo) < 6:
            self.label_chyba.text = "Heslo musí mít alespoň 6 znaků"
            self.label_chyba.visible = True
            return False
            
        self.label_chyba.visible = False
        return True
        
    def ziskej_data_uzivatele(self):
        """Vrátí data z formuláře pro vytvoření uživatele"""
        if not self.validuj_form():
            return None
            
        return {
            'email': self.text_box_email.text.strip(),
            'heslo': self.text_box_heslo.text,
            'je_admin': self.check_box_admin.checked
        }
        
    def text_box_email_lost_focus(self, **event_args):
        """Validuje email při ztrátě fokusu"""
        email = self.text_box_email.text.strip()
        if not email:
            self.label_chyba.text = "Email je povinný"
            self.label_chyba.visible = True
        elif '@' not in email:
            self.label_chyba.text = "Zadejte platný email"
            self.label_chyba.visible = True
        else:
            self.label_chyba.visible = False
            
    def text_box_heslo_lost_focus(self, **event_args):
        """Validuje heslo při ztrátě fokusu"""
        heslo = self.text_box_heslo.text
        if not heslo:
            self.label_chyba.text = "Heslo je povinné"
            self.label_chyba.visible = True
        elif len(heslo) < 6:
            self.label_chyba.text = "Heslo musí mít alespoň 6 znaků"
            self.label_chyba.visible = True
        else:
            self.label_chyba.visible = False