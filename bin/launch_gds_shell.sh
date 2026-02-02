#!/bin/bash
cd /home/jackwayne/Desktop/Optical_computing
source bin/activate_env.sh
python3 -i -c "
import gdsfactory as gf
gf.gpdk.PDK.activate()
print('')
print('=== GDSFactory + KLayout Ready ===')
print('')
print('Quick start:')
print('  c = gf.Component(\"mydesign\")')
print('  c << gf.components.ring_single(radius=5)')
print('  c.show()  # Opens in KLayout')
print('')
print('Browse components: dir(gf.components)')
print('')
"
