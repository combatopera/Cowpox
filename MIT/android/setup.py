from distutils.core import setup, Extension
import os

library_dirs = ['libs/' + os.environ['ARCH']] # XXX: What does this do?
lib_dict = {
    'sdl2': ['SDL2', 'SDL2_image', 'SDL2_mixer', 'SDL2_ttf']
}
sdl_libs = lib_dict.get(os.environ['BOOTSTRAP'], []) # FIXME: Breaks incremental build.

modules = [Extension('android._android',
                     ['android/_android.c', 'android/_android_jni.c'],
                     libraries=sdl_libs + ['log'],
                     library_dirs=library_dirs),
           Extension('android._android_billing',
                     ['android/_android_billing.c', 'android/_android_billing_jni.c'],
                     libraries=['log'],
                     library_dirs=library_dirs)]

setup(name='android',
      packages=['android'],
      package_dir={'android': 'android'},
      ext_modules=modules
      )
