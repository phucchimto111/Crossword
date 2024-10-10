import sys

from crossword import *
import copy


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        domain_copy = copy.deepcopy(self.domains)
        for var in domain_copy:
            for word in domain_copy[var]:
                if len(word) != var.length:
                    self.domains[var].remove(word)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        revised = False

        if self.crossword.overlaps[x, y] is not None:
            x_overlap, y_overlap = self.crossword.overlaps[x, y]

            # Make copy of domains
            x_domain_copy = copy.deepcopy(self.domains[x])

            # Loop through every value in domain x
            for x_word in x_domain_copy:
                # matched used to check a value of x has corsponding value of y
                matched = False
                for y_word in self.domains[y]:
                    if x_word[x_overlap] == y_word[y_overlap]:
                        matched = True
                        # No need to check remain value of y
                        break

                if not matched:
                    # Remove value from domain of x
                    self.domains[x].remove(x_word)
                    revised = True

        return revised


    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if arcs is None:
            queue = [(x, y) for x, y in self.crossword.overlaps]
        else:
            queue = [arc for arc in arcs]

        # While queue is not empty
        while len(queue) != 0:
            # Dequeue
            x, y = queue.pop(0)
            if self.revise(x, y):
                if len(self.domains[x]) == 0:
                    return False
                # For each other neighbor of X (not Y)
                for z in self.crossword.neighbors(x):
                    if z != y:
                        queue.append((z, x))
        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        for var in self.domains:
            if var not in assignment:
                return False
        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        # Check all value are distinct by check number of value with its set
        # Becase set only contain unique value
        words = [value for value in assignment]
        if len(words) != len(set(words)):
            return False

        # Check value is correct length
        for var in assignment:
            if var.length != len(assignment[var]):
                return False

        # Check no conflict between neighbors var
        for var in assignment:
            for neighbor in self.crossword.neighbors(var):
                if neighbor in assignment:
                    x_overlap, y_overlap = self.crossword.overlaps[var, neighbor]
                    if assignment[var][x_overlap] != assignment[neighbor][y_overlap]:
                        return False

        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        word_dict = {}
        neighbors = self.crossword.neighbors(var)

        for word in self.domains[var]:
            # Keep track of eliminated word
            eliminated = 0

            for neighbor in neighbors:
                if neighbor not in assignment:
                    x_overlap, y_overlap = self.crossword.overlaps[var, neighbor]
                    for neighbor_word in self.domains[neighbor]:
                        if word[x_overlap] != neighbor_word[y_overlap]:
                            eliminated += 1
            # Add value hueristic to dict
            word_dict[word] = eliminated

            # Sort
            sorted_list = [item[0] for item in sorted(word_dict.items(), key=lambda item: item[1])]

        return sorted_list

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        choice_dict = {}

        # iterating through variables in domains
        for variable in self.domains:
            # iterating through variables in assignment
            if variable not in assignment:
                # if variable is not yet in assigment, add it to temp dict
                choice_dict[variable] = self.domains[variable]

        choice_dict = dict(sorted(choice_dict.items(), key=lambda item: len(item[1])))

        # If there is one element
        if len(choice_dict) == 1:
            return list(choice_dict.keys())[0]

        # Else check with its degree
        choice = sorted(choice_dict.keys(), key=lambda key: len(self.crossword.neighbors(key)), reverse=True)

        return choice[0]

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if len(assignment) == len(self.domains):
            return assignment

        # selecting one of unassigned variables
        variable = self.select_unassigned_variable(assignment)

        # iterating through words in that variable
        for value in self.domains[variable]:
            # making assignment copy, with updated variable value
            assignment_copy = assignment.copy()
            assignment_copy[variable] = value
            # checking for consistency, getting result of that new assignment backtrack
            if self.consistent(assignment_copy):
                result = self.backtrack(assignment_copy)
                if result is not None:
                    return result
        return None


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
