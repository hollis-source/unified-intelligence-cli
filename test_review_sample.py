"""Sample code for PR review testing - Phase 8A.

This file contains deliberately simple code to test
the auggie-powered code review functionality.
"""

def calculate_average(numbers):
    """Calculate average of numbers."""
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)


def is_even(number):
    """Check if number is even."""
    return number % 2 == 0


class StringHelper:
    """Helper class for string operations."""

    @staticmethod
    def reverse(text):
        """Reverse a string."""
        return text[::-1]

    @staticmethod
    def count_vowels(text):
        """Count vowels in text."""
        vowels = "aeiouAEIOU"
        count = 0
        for char in text:
            if char in vowels:
                count += 1
        return count
