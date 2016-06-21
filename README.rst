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


Test-case Usage Examples
------------------------

.. code-block:: python

    # from tests/test_contexts.py

    def test_apply_alchemy(self):
        # for our test today, we will be doing some basic alchemy
        inventory = [
            "aqua fortis",
            "glauber's salt",
            "lunar caustic",
            "mosaic gold",
            "plumbago",
            "salt",
            "tin salt",
            "butter of tin",
            "stibnite",
            "naples yellow",
        ]

        # backstory:
        # ~~~~~~~~~~
        #
        # falling asleep last night, you finally figured out how to complete
        # your life's work: discovering the elusive *elixir of life*!
        #
        # and it's only two ingredients! and you have them on hand!
        #
        # ...
        #
        # unfortunately this morning you can't remember which two
        # ingredients it was.
        #
        # you'll know it once you've gotten it, just have to try out
        # all possible mixtures. (should be safe enough, right?)

        forgotten_elixir_of_life = set(random.sample(inventory, 2))

        discoveries_today = set(["frantic worry", "breakfast"])

        # ok time to go do some arbitrary alchemy!
        #
        # game plan:
        alchemy_ctx = Context()

        # you'll grab one ingredient,
        selected_first_ctx = alchemy_ctx.select("/inventory").each()
        first_substance = selected_first_ctx.value

        # and another,
        selected_second_ctx = selected_first_ctx.select("/inventory").each()
        second_substance = selected_second_ctx.value

        # take them to your advanced scientific mixing equipment,
        workstation_ctx = selected_second_ctx.select("/workstation")

        # (btw this is your advanced scientific procedure that you are
        # 100% certain will tell you what some mixture is)
        def mix(first, second):
            """takes two ingredients and returns the resulting substance"""
            if set([first, second]) == forgotten_elixir_of_life:
                return "elixir of life"
            return "some kind of brown goo"

        # then you'll mix your ingredients...
        mixed_ctx = workstation_ctx.apply(
            mix,
            first_substance, second_substance
        )
        resulting_mixture = mixed_ctx.value

        # ... and! in today's modern age, scientists now know to record their
        # results!
        mixed_ctx.select("/discoveries").append_value(resulting_mixture)

        # got it? good!
        result = run_policy(
            alchemy_ctx.finalize(),
            {"inventory": inventory, "discoveries": discoveries_today}
        )

        # in a flurry of excitement, i bet you didn't even stop to
        # look at your discoveries as you made them!
        #
        # well, let's see...

        self.assertIn("elixir of life", result["discoveries"])

    def test_apply_dangerous_alchemy(self):
        # nice job! and you even finished in time to go foraging for
        # more ingredients!
        inventory = [
            "aqua fortis",
            "glauber's salt",
            "lunar caustic",
            "mosaic gold",
            "plumbago",
            "salt",
            "tin salt",
            "butter of tin",
            "stibnite",
            "naples yellow",

            # nice find
            "anti-plumbago"
        ]

        # but unfortunately, it's the next day, and the same thing
        # has happened to you! except this time it was for your
        # other life's goal: discover the ~elixir of discord~!
        #
        # well, since it was so easy...

        whatever_concoction = set(['some ingredients'])

        discoveries_today = set([])
        should_be_fine = 'overconfidence' not in discoveries_today
        assert should_be_fine

        # doing alchemy la la la
        alchemy_ctx = Context()

        # grabbin' things off shelves
        selected_first_ctx = alchemy_ctx.select("/inventory").each()
        first_substance = selected_first_ctx.value

        selected_second_ctx = selected_first_ctx.select("/inventory").each()
        second_substance = selected_second_ctx.value

        # got our ingredients
        got_ingredients_ctx = selected_second_ctx

        workstation_ctx = got_ingredients_ctx.select("/workstation")

        # mixin' - don't stop to think
        def mix(first, second):
            mixture = set([first, second])
            if mixture == whatever_concoction:
                return 'missing elixir'
            if mixture == set(['plumbago', 'anti-plumbago']):
                return 'concentrated danger'
            return 'more brown goo'

        mixed_ctx = workstation_ctx.apply(
            mix,
            first_substance, second_substance
        )
        resulting_mixture = mixed_ctx.value

        mixed_ctx.select("/discoveries").append_value(resulting_mixture)

        # wait wait wait!!
        def danger(mixture):
            if mixture == 'concentrated danger':
                return True
            return False

        # we can't have that.
        danger_ctx = mixed_ctx.check(
            danger,
            resulting_mixture
        )
        danger_ctx.forbid()

        # moral:
        #
        # a strong understanding of policies and processes facilitates a
        # hazard-free lab environment.
        result = run_policy(
            alchemy_ctx.finalize(),
            {"inventory": inventory, "discoveries": discoveries_today}
        )

        self.assertIn("errors", result)
        self.assertTrue(len(result['errors']))



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
