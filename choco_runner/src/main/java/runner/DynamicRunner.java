package runner;

import org.chocosolver.solver.Model;
import org.chocosolver.solver.Solver;
import org.chocosolver.solver.variables.IntVar;

import java.util.Arrays;

/**
 * Small Choco smoke test: solve 4-Queens.
 *
 * If this runs and prints at least one valid solution, both Java and Choco are working.
 */
public class DynamicRunner {
    public static void main(String[] args) {
        int n = 4;
        Model model = new Model("4-Queens Smoke Test");

        // q[i] is the column of the queen placed on row i.
        IntVar[] q = model.intVarArray("q", n, 0, n - 1);

        // One queen per column.
        model.allDifferent(q).post();

        // No two queens on same diagonal.
        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                model.arithm(q[i], "!=", q[j], "+", j - i).post();
                model.arithm(q[i], "!=", q[j], "-", j - i).post();
            }
        }

        Solver solver = model.getSolver();

        int count = 0;
        while (solver.solve()) {
            count++;
            System.out.println("SOLUTION " + count + ": " + Arrays.toString(q));
        }

        if (count == 0) {
            System.out.println("NO_SOLUTION_FOUND");
        } else {
            System.out.println("TOTAL_SOLUTIONS=" + count);
        }

        solver.printStatistics();
    }
}
