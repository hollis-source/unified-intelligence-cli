"""Monad entity for task sequencing with effects.

Clean Architecture: Entity layer.
SOLID: SRP - represents only monadic computation.

Note: This is a runtime value wrapper for monadic computations,
NOT an AST node. The Monad wraps values and provides bind (>>)
for sequencing effectful computations. For representing bind
operations in the AST, use a separate Bind entity.
"""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Monad:
    """
    Represents a monadic computation for sequencing tasks with effects.

    Monads encapsulate values and provide operations for composing
    computations while handling effects (errors, async, state, etc.).

    Follows monad laws:
    - Left identity: unit(a) >>= f == f(a)
    - Right identity: m >>= unit == m
    - Associativity: (m >>= f) >>= g == m >>= (lambda x: f(x) >>= g)

    Clean Code principles:
    - Immutable: frozen=True
    - Composable: bind (>>=) for chaining
    - Lawful: Follows mathematical monad laws
    - Type-safe: Type hints for clarity

    Attributes:
        value (Any): The wrapped value.

    Example:
        m = Monad.unit(5)
        result = m >>= (lambda x: Monad.unit(x * 2)) >>= (lambda x: Monad.unit(x + 1))
        # result == Monad(value=11)
    """
    value: Any

    @classmethod
    def unit(cls, value: Any) -> 'Monad':
        """
        Wraps a value into a Monad (monadic unit/return/pure).

        This is the monadic "return" operation, lifting a value
        into the monadic context.

        Args:
            value (Any): The value to wrap.

        Returns:
            Monad: A new Monad instance containing the value.

        Example:
            m = Monad.unit(42)  # Monad(value=42)
        """
        return cls(value)

    def __rshift__(self, func: Callable[[Any], 'Monad']) -> 'Monad':
        """
        Binds the monad's value to a function that returns a Monad (>>= operator).

        This is the monadic "bind" operation, enabling sequencing of
        computations with effects.

        Args:
            func (Callable[[Any], Monad]): A function that takes the wrapped value
                and returns a new Monad.

        Returns:
            Monad: The result of applying the function to the value.

        Example:
            m = Monad.unit(3)
            result = m >>= (lambda x: Monad.unit(x * 2))  # Monad(value=6)
        """
        return func(self.value)
