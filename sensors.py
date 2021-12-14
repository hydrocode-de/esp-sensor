from urandom import randint


def random_integer(controller, **kwargs):
    """
    Development only, replace this function

    The function has to accept kwargs. In the config you can
    specify which attributes should be passed to the function.
    It will always pass a reference to the BoardController
    instance, which called the function as controller
    """
    return randint(0, 100)
