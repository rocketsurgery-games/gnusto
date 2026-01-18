# Language model implementation

The core innovation in FrotzVM is the use of a language model to parse and interpret user input; and to adapt world state to user-visible descriptions. 



## Result context
What do we _really_ want from effects like `(success :context (description "..."))`? Consider pulling all the context (e.g., `:context ((timer-display ...`) into explicit ui-effects that give instructions on how context should be displayed to the user.

This is best addressed when we start bolting on the LM adapter for real. This will give us a much clearer idea of what we need to solve real needs.

