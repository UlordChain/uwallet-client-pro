from kivy.app import App
from kivy.factory import Factory
from kivy.properties import ObjectProperty
from kivy.lang import Builder
from decimal import Decimal

Builder.load_string('''

<AmountDialog@Popup>
    id: popup
    title: _('Amount')
    AnchorLayout:
        anchor_x: 'center'
        BoxLayout:
            orientation: 'vertical'
            size_hint: 0.8, 1
            BoxLayout:
                size_hint: 1, None
                height: '80dp'
                Label:
                    id: a
                    btc_text: (kb.amount + ' ' + app.base_unit) if kb.amount else ''
                    fiat_text: (kb.fiat_amount + ' ' + app.fiat_unit) if kb.fiat_amount else ''
                    text1: ((self.fiat_text if kb.is_fiat else self.btc_text) if app.fiat_unit else self.btc_text) if self.btc_text else ''
                    text2: ((self.btc_text if kb.is_fiat else self.fiat_text) if app.fiat_unit else '') if self.btc_text else ''
                    text: self.text1 + "\\n" + "[color=#8888ff]" + self.text2 + "[/color]"
                    halign: 'right'
                    size_hint: 1, None
                    font_size: '22dp'
                    height: '80dp'
            Widget:
                size_hint: 1, 0.2
            GridLayout:
                id: kb
                amount: ''
                fiat_amount: ''
                is_fiat: False
                on_fiat_amount: if self.is_fiat: self.amount = app.fiat_to_btc(self.fiat_amount)
                on_amount: if not self.is_fiat: self.fiat_amount = app.btc_to_fiat(self.amount)
                size_hint: 1, None
                update_amount: popup.update_amount
                height: '300dp'
                cols: 3
                KButton:
                    text: '1'
                KButton:
                    text: '2'
                KButton:
                    text: '3'
                KButton:
                    text: '4'
                KButton:
                    text: '5'
                KButton:
                    text: '6'
                KButton:
                    text: '7'
                KButton:
                    text: '8'
                KButton:
                    text: '9'
                KButton:
                    text: '.'
                KButton:
                    text: '0'
                KButton:
                    text: '<'
                Button:
                    id: but_max
                    opacity: 1 if root.show_max else 0
                    disabled: not root.show_max
                    size_hint: 1, None
                    height: '48dp'
                    text: 'Max'
                    on_release:
                        kb.is_fiat = False
                        kb.amount = app.get_max_amount()
                Button:
                    id: button_fiat
                    size_hint: 1, None
                    height: '48dp'
                    text: (app.base_unit if kb.is_fiat else app.fiat_unit) if app.fiat_unit else ''
                    on_release:
                        if app.fiat_unit: popup.toggle_fiat(kb)
                Button:
                    size_hint: 1, None
                    height: '48dp'
                    text: 'Clear'
                    on_release:
                        kb.amount = ''
                        kb.fiat_amount = ''
            Widget:
                size_hint: 1, 0.2
            BoxLayout:
                size_hint: 1, None
                height: '48dp'
                Widget:
                    size_hint: 1, None
                    height: '48dp'
                Button:
                    size_hint: 1, None
                    height: '48dp'
                    text: _('OK')
                    on_release:
                        root.callback(a.btc_text)
                        popup.dismiss()
''')

from kivy.properties import BooleanProperty

class AmountDialog(Factory.Popup):
    show_max = BooleanProperty(False)
    def __init__(self, show_max, amount, cb):
        Factory.Popup.__init__(self)
        self.show_max = show_max
        self.callback = cb
        if amount:
            self.ids.kb.amount = amount

    def toggle_fiat(self, a):
        a.is_fiat = not a.is_fiat

    def update_amount(self, c):
        kb = self.ids.kb
        amount = kb.fiat_amount if kb.is_fiat else kb.amount
        if c == '<':
            amount = amount[:-1]
        elif c == '.' and amount in ['0', '']:
            amount = '0.'
        elif amount == '0':
            amount = c
        else:
            try:
                Decimal(amount+c)
                amount += c
            except:
                pass
        if kb.is_fiat:
            kb.fiat_amount = amount
        else:
            kb.amount = amount
