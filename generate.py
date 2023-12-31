import sys
import copy
from crossword import *


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

        domains = copy.deepcopy(self.domains)
        for domain in domains:
            dom = copy.deepcopy(self.domains[domain])
            for node in dom:
                # Remove words that do not have the same length as the variable
                if len(node) != domain.length:
                    self.domains[domain].remove(node)


    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        revision= False
        overlap  = self.crossword.overlaps[x, y]

        # No revision when there is no overlap between the variables
        if overlap is None:
            return revision
        
        domains_x = copy.deepcopy(self.domains[x])
        domains_y = copy.deepcopy(self.domains[y])
        
        for node in domains_x:
            found = False
            for node2 in domains_y:
                if node[overlap[0]] == node2[overlap[1]]:
                    found = True
            
            # Remove word that did not match any other word in the intersection
            if not found:
                self.domains[x].remove(node)
                revision = True

        return revision


    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if not arcs:
            # Construct arcs from the variables and their neighbors
            arcs = [(var, neighbor) for var in self.domains.keys() for neighbor in self.crossword.neighbors(var)]


        while arcs:
            var1, var2 = arcs.pop(0)  # Remove an arc from the list

            if self.revise(var1, var2):
                if not self.domains[var1]:  # Check if domain is empty
                    return False

                for neighbor in self.crossword.neighbors(var1):
                    if neighbor != var2:
                        arcs.append((neighbor, var1))  # Add neighbors to the queue

        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        if len(assignment.keys()) == len(self.domains.keys()):
                return True
        return False

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """

        used_values = set()  # To keep track of already used values
        for variable, value in assignment.items():
            # Check if values are distinct
            if value in used_values:
                return False
            used_values.add(value)
            
            # Check if value length matches variable's length
            if len(value) != variable.length:
                return False
            
            # Check for conflicts with neighboring variables
            for neighbor in self.crossword.neighbors(variable):
                if neighbor in assignment:
                    neighbor_value = assignment[neighbor]
                    overlap = self.crossword.overlaps[variable,neighbor]
                    if neighbor_value[overlap[1]] != value[overlap[0]]:
                        return False
        return True
    

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        ordered_values = []
        
        # Populate a list with all the values in the variable's domain and the number of values they ruled out
        for value in self.domains[var]:
            counter = 0
            for neighbor in self.crossword.neighbors(var):
                intersection = self.crossword.overlaps[var,neighbor]
                for value2 in self.domains[neighbor]:
                    # Count the number of words in the neighbor variable that conflict with a word of the given variable 
                    if value[intersection[0]] != value2[intersection[1]] and value2 not in assignment.keys():
                        counter +=1
            ordered_values.append((value,counter))

        # Sort list based on the values that got ruled out in ascending order 
        ordered_values.sort(key=lambda x: x[1])

        return [value for value, _ in ordered_values]

   
    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        unassigned_variables = [var for var in self.domains.keys() if var not in assignment]
    
        if not unassigned_variables:
            return None
        
        # Sort unassigned variables based on the minimum number of remaining values
        unassigned_variables.sort(key=lambda var: (len(self.domains[var]), -len(self.crossword.neighbors(var))))
        
        return unassigned_variables[0]

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if self.assignment_complete(assignment):
            return assignment 
        
        variable = self.select_unassigned_variable(assignment)

        if variable is None:
            return assignment
        
        for value in self.order_domain_values(variable, assignment):
            assignment[variable] = value
            if self.consistent(assignment):
                arcs = [(var, variable) for var in self.crossword.neighbors(variable)]
                inference_result = self.ac3(arcs)
                if inference_result:
                    # Recursively call backtrack to construct the solution
                    result = self.backtrack(assignment)
                    if result is not None:
                        return result
            else:
                del assignment[variable]

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
