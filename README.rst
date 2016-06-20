calcifer
========

|Version| |Downloads| |Status| |Coverage| |License|

A Python based policy framework.


Installation
------------

::

    pip install calcifer


.. include:: contributing.rst


Development
-----------

1. Create a new virtual environment
2. Install development requirements from *dev-requirements.txt*
3. Run tests  ``nosetests``
4. `detox`_ is installed and will run the test suite across all supported python platforms
5. `python setup.py build_sphinx` will generate documentation into *build/sphinx/html*

TL;DR
+++++

::

    $ virtualenv env
    $ ./env/bin/pip install -qr dev-requirements.txt
    $ source env/bin/activate
    (env) $ nosetests
    (env) $ python setup.py build_sphinx
    (env) $ detox


.. include:: ../HISTORY.rst


License
-------

`The Calcifer library is distributed under the MIT License <https://github.com/DramaFever/calcifer/blob/master/LICENSE>`_


.. _detox: https://testrun.org/tox/

.. |Version| image:: https://badge.fury.io/py/calcifer.svg?
   :target: http://badge.fury.io/py/calcifer

.. |Status| image:: https://travis-ci.org/DramaFever/calcifer.svg?branch=master
   :target: https://travis-ci.org/DramaFever/calcifer

.. |Coverage| image:: https://img.shields.io/coveralls/DramaFever/calcifer.svg?
   :target: https://coveralls.io/r/DramaFever/calcifer

.. |Downloads| image:: https://pypip.in/d/calcifer/badge.svg?
   :target: https://pypi.python.org/pypi/calcifer

.. |License| image:: https://pypip.in/license/calcifer/badge.svg?
   :target: https://calcifer.readthedocs.org
