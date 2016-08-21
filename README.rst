Calcifer
========

|Docs| |Version| |Status| |License|

**Calcifer** is designed to provide interfaces for describing the evaluation
and processing of nested higher-order data structures by nested definitions of
policy rules.

Policies may be used to evaluate some source object both for validation, and to
generate template descriptions of a "complete" version of that object. This
evaluation is done at runtime and can hook into arbitrary functions, e.g.
for choosing policies based on some current system state. (Hypermedia style)

Policies may be defined with implicit non-determinism, allowing the
specification of multiple policy choices with minimal boilerplate for handling
the aggregation of results. (Prolog style)

Calcifer also provides a system by which application-layer code can annotate
specific policy rules, making the point-in-time context of a policy computation
into a first-class value. This allows for rich error handling, by being aware
of specific points of policy failure and allowing annotated policy rules
to control the formatting of their own errors.

This library was written to facilitate the development of a hypermedia
subscription management API. This library's design is informed by that API's
goals of business logic cohesion and adaptability to changing policy rules.
A major goal for that project has been to alleviate client integrations of
their need to perform any policy determination locally; Calcifer has stemmed
largely from this effort.


Installation
------------

::

    pip install calcifer


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

.. |Docs| image:: https://readthedocs.org/projects/calcifer/badge/?version=latest
    :alt: Documentation Status
    :scale: 100%
    :target: https://calcifer.readthedocs.io/en/latest/?badge=latest

.. |Version| image:: https://img.shields.io/pypi/v/calcifer.svg?maxAge=2592000
   :target: https://pypi.python.org/pypi/calcifer

.. |Status| image:: https://travis-ci.org/DramaFever/calcifer.svg?branch=master
   :target: https://travis-ci.org/DramaFever/calcifer

.. |License| image:: https://img.shields.io/badge/license-MIT-blue.svg
   :target: https://raw.githubusercontent.com/DramaFever/calcifer/master/LICENSE
