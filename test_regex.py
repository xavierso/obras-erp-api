import re

text_diam = 'P-805 Nueva Partida 1 ud 46,00 € 46,00 €'
text_excel = '01.01 Nueva Partida ud 1 55.00€ 0.00% 55.00€'
text_blasco = '01.01 M2 PICADO, PICOTEADO O RASPADO DE PARAMENTOS VERTICALES PATIOS'

pattern_diam = re.compile(r'^([\w\.\-]+)\s+(.*?)\s+([\d,\.]+)\s+([a-zA-Z]{1,4})\s+([\d,\.]+)\s*€?\s+([\d,\.]+)\s*€?$')
print("DIAM:", pattern_diam.match(text_diam).groups() if pattern_diam.match(text_diam) else None)

pattern_excel = re.compile(r'^([\w\.\-]+)\s+(.*?)\s+([a-zA-Z]{1,4})\s+([\d,\.]+)\s+([\d,\.]+)\s*€?(?:\s+[\d,\.]+\s*%)?\s+([\d,\.]+)\s*€?$')
print("EXCEL:", pattern_excel.match(text_excel).groups() if pattern_excel.match(text_excel) else None)

pattern_blasco = re.compile(r'^([\w\.\-]+)\s+([a-zA-Z0-9]{1,4})\s+(.*?)$')
print("BLASCO:", pattern_blasco.match(text_blasco).groups() if pattern_blasco.match(text_blasco) else None)
