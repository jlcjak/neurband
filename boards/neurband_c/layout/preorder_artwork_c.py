"""Add clipped cell-envelope and visible connector service artwork."""
from native_check_c import *
def main():
 t=load();save(t,BUILD/'before-service-artwork.kicad_pcb')
 def line(a,b,ly):t.append(['gr_line',['start',*map(num,a)],['end',*map(num,b)],['stroke',['width','.15'],['type','solid']],['layer',json.dumps(ly)],ident()])
 def text(s,x,y,ly):
  effects=['effects',['font',['size','1','1'],['thickness','.15']]]
  if ly=='B.SilkS':effects.append(['justify','mirror'])
  t.append(['gr_text',json.dumps(s),['at',num(x),num(y),'0'],['layer',json.dumps(ly)],ident(),effects])
 # The upper part of the cell lies beyond the board. Draw the three surviving edges.
 line((11,.2),(11,21.7),'B.SilkS');line((11,21.7),(23,21.7),'B.SilkS');line((23,21.7),(23,.2),'B.SilkS');text('CELL',17,18.3,'B.SilkS')
 # This strip is above the connector's closed housing, outside the actuator envelope.
 text('CONTACTS DOWN',18,20.28,'F.SilkS')
 save(t);check('service-artwork')
if __name__=='__main__':main()
