**Submitted To:**

**Mam Mehmona Salam**

**Submitted By:**

[Student Name(s) / Group Name]

**Course:**

Design and Analysis of Algorithms (DAA)

**Project Title:**

SocialGraph Studio

**DEPARTMENT OF COMPUTER SCIENCE**

# Table of Contents

1. Introduction  
   1.1 Background  
   1.2 Problem Statement  
   1.3 Objectives  
   1.4 Scope

2. Project Overview  
   2.1 Application Summary  
   2.2 Major Modules

3. Graph Model and Input Handling  
   3.1 Supported Input Formats  
   3.2 Graph Assumptions  
   3.3 Manual Graph Building

4. Algorithms and Theory  
   4.1 Breadth-First Search (BFS)  
   4.2 Depth-First Search (DFS)  
   4.3 Shortest Social Distance  
   4.4 Connected Components  
   4.5 Time Complexity Analysis

5. System Design and Implementation  
   5.1 Frontend Architecture  
   5.2 Visualization Engine  
   5.3 Traversal Animation Logic  
   5.4 Analytics and Reporting

6. User Interface and Features  
   6.1 Studio View  
   6.2 Data Input View  
   6.3 Analytics View  
   6.4 Explanation View

7. Working Methodology  
   7.1 Loading a Graph  
   7.2 Running BFS and DFS  
   7.3 Inspecting Results

8. Testing and Evaluation  
   8.1 Functional Test Cases  
   8.2 Observations

9. Limitations  
10. Future Enhancements  
11. Conclusion  
12. References

# 1. INTRODUCTION

## 1.1 Background

Graphs are one of the most important data structures in computer science because they model relationships between entities. In social networks, each user can be represented as a vertex, while each connection between users can be represented as an edge. Graph traversal algorithms such as Breadth-First Search (BFS) and Depth-First Search (DFS) are widely used to explore connectivity, discover communities, and determine the shortest path between nodes in an unweighted network.

SocialGraph Studio is an interactive browser-based project designed to demonstrate these concepts visually. Instead of presenting graphs only in theory, the application allows the user to create, edit, and explore a social network in real time.

## 1.2 Problem Statement

Students often understand traversal algorithms better when they can observe the algorithm step by step. However, many textbook examples are static and do not show how a queue, stack, visited set, or traversal order changes during execution.

This project solves that gap by providing:

- a live social network graph,
- interactive BFS and DFS traversal animations,
- visible queue and stack states,
- shortest social distance calculation,
- community detection through connected components,
- and analytics that summarize the graph structure.

## 1.3 Objectives

The project was developed with the following objectives:

- Model a social network as an undirected graph.
- Allow users to paste custom graph data or build a graph manually.
- Visualize BFS and DFS traversal in an interactive and educational way.
- Show the real queue for BFS and the real stack for DFS.
- Highlight the current node, visited nodes, source node, and target node.
- Compute the shortest social distance between two selected users.
- Identify connected components and graph density.
- Present algorithm theory, pseudocode, and complexity analysis in the interface.

## 1.4 Scope

The current version focuses on:

- client-side graph analysis in the browser,
- social network style graph visualization,
- BFS and DFS traversal only,
- undirected graphs,
- and educational exploration of graph behavior.

The project does not include:

- backend storage,
- authentication,
- persistent databases,
- weighted edges,
- directed graph analysis,
- or real external social media APIs.

# 2. PROJECT OVERVIEW

## 2.1 Application Summary

SocialGraph Studio is a single-page web application built with HTML, CSS, and JavaScript. It is designed as a DAA demonstration project for graph traversal algorithms. The application is completely offline after loading in the browser and does not require any package installation or server setup.

The interface contains four major areas:

- a live graph workspace,
- a data input and manual builder section,
- an analytics section,
- and a theory section with algorithm explanations.

## 2.2 Major Modules

The project is divided into the following logical modules:

| Module | Purpose |
| --- | --- |
| Graph Parser | Reads adjacency-list or edge-list style input and converts it into nodes and edges. |
| Graph Builder | Allows manual addition of users and connections. |
| Graph Renderer | Draws the social network as an SVG-based interactive visualization. |
| Traversal Engine | Runs BFS or DFS and records each step of the algorithm. |
| Structure Visualizer | Displays queue and stack states during traversal. |
| Analytics Engine | Computes connected components, density, traversal order, and shortest path. |
| Theory Panel | Explains BFS and DFS with pseudocode and time complexity. |

# 3. GRAPH MODEL AND INPUT HANDLING

## 3.1 Supported Input Formats

The application accepts graph input in two readable formats:

### Edge List Format

Each line describes one connection:

```text
Ayesha-Bilal
Bilal-Hina
Hina-Sara
```

### Adjacency List Format

Each line begins with a user name followed by connected users:

```text
Ayesha: Bilal, Hina
Bilal: Usman, Sara
Sara: Noor, Laiba
```

The parser also supports separators such as commas, semicolons, pipes, and spaces where appropriate.

## 3.2 Graph Assumptions

The project follows these graph rules:

- Each user is treated as a vertex.
- Each relationship is treated as an undirected edge.
- Duplicate edges are ignored.
- Self-loops are ignored.
- User names are normalized by trimming extra spaces.
- Neighbor processing is sorted alphabetically to keep traversal order deterministic.

This deterministic ordering is useful in teaching because the same input always produces the same BFS and DFS sequence.

## 3.3 Manual Graph Building

In addition to typed input, the application includes a manual builder. Users can:

- add a new user,
- select two users from dropdowns,
- add a relationship between them,
- remove a relationship,
- or clear and reload the graph.

This makes the project suitable for live classroom demonstrations where the teacher can build examples in front of students.

# 4. ALGORITHMS AND THEORY

## 4.1 Breadth-First Search (BFS)

BFS explores the graph level by level using a queue. In SocialGraph Studio, BFS is used for:

- influence propagation,
- shortest social distance in unweighted graphs,
- and level-based visualization of traversal order.

The BFS implementation records each dequeue operation, the nodes that are newly enqueued, the current level, and the queue state after every step.

### BFS Pseudocode

```text
mark source visited
enqueue source

while queue is not empty:
    current = dequeue()
    for each neighbor of current:
        if neighbor is not visited:
            mark neighbor visited
            enqueue(neighbor)
```

## 4.2 Depth-First Search (DFS)

DFS explores deeply before backtracking. It uses a stack and is best for:

- deep relationship exploration,
- connected component discovery,
- and understanding LIFO behavior.

The application shows the stack contents, push and pop operations, and traversal narration at each step.

### DFS Pseudocode

```text
push source onto stack

while stack is not empty:
    current = pop()
    if current is not visited:
        mark current visited
        for each neighbor of current:
            if neighbor is not visited:
                push(neighbor)
```

## 4.3 Shortest Social Distance

The application uses BFS to calculate the shortest path between the selected source and target users. If a path exists, the app displays:

- the path sequence,
- the number of hops,
- and a message describing the social distance.

If no path exists, the app reports that the users belong to different communities.

## 4.4 Connected Components

Connected components are used to identify communities in the social graph. A connected component is a set of users that can reach each other through some path.

The project uses graph traversal to collect nodes in each component and then displays them as community groups in the analytics section.

## 4.5 Time Complexity Analysis

Both BFS and DFS run in:

**O(V + E)**

where:

- **V** is the number of vertices,
- **E** is the number of edges.

This complexity is appropriate for graph traversal because each vertex and edge is processed a limited number of times.

# 5. SYSTEM DESIGN AND IMPLEMENTATION

## 5.1 Frontend Architecture

The project is implemented as a static frontend application using:

- **HTML** for structure,
- **CSS** for layout and styling,
- **JavaScript** for graph logic, animation, and analytics.

There is no backend server. The entire project runs directly in the browser.

## 5.2 Visualization Engine

The graph is rendered using SVG, which gives the project smooth and scalable visual output. The renderer supports:

- labeled nodes,
- curved relationship links,
- active traversal highlights,
- source and target highlighting,
- visited-state styling,
- draggable nodes,
- and tooltip-based node information.

The layout engine groups disconnected components into visible clusters so the graph remains readable even when the network is spread across multiple communities.

## 5.3 Traversal Animation Logic

The traversal engine creates a step-by-step record for BFS or DFS. Each step stores:

- the currently processed node,
- the parent node,
- the structure state before and after the operation,
- nodes added to the queue or stack,
- and operations counted during traversal.

The visual controls allow the user to:

- start traversal,
- pause traversal,
- move one step at a time,
- reset the animation,
- and adjust animation speed.

## 5.4 Analytics and Reporting

The analytics section summarizes the graph using live counters and charts. It shows:

- total number of users,
- total number of connections,
- graph density,
- number of connected components,
- BFS level distribution,
- component sizes,
- traversal order,
- and an operation estimate.

This makes the application useful not only as a visual demo but also as a small analysis tool for social graphs.

# 6. USER INTERFACE AND FEATURES

## 6.1 Studio View

The studio view is the main working area. It includes:

- algorithm selection between BFS and DFS,
- source and target user selectors,
- speed control,
- start, step, pause, and reset buttons,
- queue/stack visualization,
- and a live step narration panel.

## 6.2 Data Input View

The data input section lets the user:

- paste a custom social graph,
- load the graph into the workspace,
- add a new user manually,
- create or remove edges,
- and work with the default sample network.

This section is important for classroom use because it allows the teacher to change the graph instantly during discussion.

## 6.3 Analytics View

The analytics view contains:

- BFS influence propagation chart,
- connected components chart,
- connectivity status,
- traversal order output,
- and the complexity report.

## 6.4 Explanation View

The explanation view provides:

- BFS theory,
- DFS theory,
- pseudocode,
- and a clear explanation of the time complexity.

This ensures the project is educational, not only visual.

# 7. WORKING METHODOLOGY

## 7.1 Loading a Graph

The user can begin by:

1. loading the default sample graph,
2. pasting a custom edge list or adjacency list,
3. or building the graph manually.

Once the graph is loaded, the application populates the user dropdowns and prepares the traversal workspace.

## 7.2 Running BFS and DFS

After selecting a source user:

- BFS can be run to observe level-wise expansion,
- DFS can be run to observe deep traversal,
- the queue or stack updates live,
- and the current step explanation changes during animation.

If a target user is selected, the app also calculates the shortest path between the source and target users.

## 7.3 Inspecting Results

While the traversal runs, the application highlights:

- the current node,
- visited nodes,
- source node,
- target node,
- and the active relationship path.

At the same time, the analytics panel updates with community, density, and traversal statistics.

# 8. TESTING AND EVALUATION

## 8.1 Functional Test Cases

The following representative test cases were considered during evaluation:

| Test Case | Expected Result |
| --- | --- |
| Load default sample graph | Graph loads successfully with users and connections. |
| Paste adjacency-list input | Graph is parsed into the correct vertices and edges. |
| Add a new user manually | New user appears in dropdowns and workspace. |
| Add a new edge manually | Connection is created and reflected in the visualization. |
| Run BFS from a selected source | Queue animation and level-order traversal appear. |
| Run DFS from a selected source | Stack animation and depth-first traversal appear. |
| Select source and target users | Shortest social distance is calculated. |
| Graph has multiple clusters | Connected components are displayed as communities. |
| Drag a node in the canvas | Node position updates interactively. |
| Reset traversal | Traversal state and narration return to the default view. |

## 8.2 Observations

The project behaves as intended for classroom-scale graphs. The most useful observations are:

- BFS is easier for students to understand when level-wise propagation is shown visually.
- DFS becomes clearer when the stack is displayed explicitly.
- The component chart helps explain community structure.
- The deterministic alphabetical sorting improves repeatability in demonstrations.
- The project remains responsive because it runs fully in the browser without backend overhead.

# 9. LIMITATIONS

The current implementation has a few limitations:

- It supports only unweighted graphs.
- It focuses on undirected relationships.
- It does not save graphs permanently across sessions.
- It does not integrate with real social media platforms.
- It is intended for medium-size classroom examples rather than very large networks.

# 10. FUTURE ENHANCEMENTS

The project can be extended in several useful ways:

- add weighted and directed graph support,
- include Dijkstra's algorithm for weighted shortest paths,
- save and reload user graphs using local storage or a backend database,
- add search and filtering for large networks,
- introduce more analytics such as centrality measures,
- and support import/export of graph files.

# 11. CONCLUSION

SocialGraph Studio is a complete educational project for demonstrating BFS, DFS, graph connectivity, and social network analysis. The application turns abstract algorithm theory into an interactive visual experience that is easier to understand and explain in class.

The project successfully shows how a graph can be modeled from real user input, traversed step by step, analyzed through connected components and density, and explained through both visualization and theory. Because it is simple to run and completely browser-based, it is suitable for live DAA demonstrations and student presentations.

# 12. REFERENCES

- Cormen, Leiserson, Rivest, and Stein, *Introduction to Algorithms*.
- Standard graph traversal theory from Design and Analysis of Algorithms coursework.
- HTML, CSS, and JavaScript documentation.
- SVG documentation for scalable vector rendering.
- BFS and DFS pseudocode and complexity concepts as implemented in the project.
