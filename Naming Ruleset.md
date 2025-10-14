# Clean Code Naming Ruleset

Based on "Clean Code" by Robert C. Martin (from Chapters 3, 4, and 17), synergized with backend codebase directory naming taxonomy best practices. This ruleset prioritizes readability, intent revelation, maintainability, and scalable structure through thoughtful naming at code and filesystem levels.

## Function and Method Naming
- **Use Descriptive Names**: Function names should clearly state what the function does without requiring readers to inspect the code. Avoid short, enigmatic names; opt for longer, expressive ones.  
  *Bad*: `testableHtml` (ambiguous).  
  *Good*: `includeSetupAndTeardownPages` (describes exact behavior).
- **Form Verb-Noun Pairs**: For methods, pair a verb (action) with a noun (object) to evoke what is being done.  
  *Example*: `postPayment()`, `deletePage()`, `save()`.
- **Use Keywords for Clarity**: Add keywords to names to clarify argument roles, especially in monadic functions.  
  *Bad*: `write(name)`.  
  *Good*: `writeField(name)` (indicates `name` is a field).
- **Avoid Flag Arguments**: Do not use booleans as arguments, as they imply the function does multiple things. Split into separate functions instead.  
  *Bad*: `render(true)` (renders for web?).  
  *Good*: `renderForWeb()`.
- **Describe Side Effects**: Names must reveal all actions, including side effects. Do not mislead about what the function does.  
  *Bad*: `checkPassword()` that also initializes a session.  
  *Good*: `attemptLoginAndInitializeSession()`.

## Variable and Argument Naming
- **Choose Descriptive and Unambiguous Names**: Variables should describe their purpose fully, avoiding abbreviations unless scope is tiny. Reevaluate names as code evolves.  
  *Bad*: `q`, `z`, `kk` (cryptic in a scoring loop).  
  *Good*: `score`, `frameIndex`, `frameNumber` (clear in context of bowling game).
- **Match Abstraction Level**: Names should reflect the class/method's abstraction level, not low-level implementation details.  
  *Example*: In a high-level processor class, use `processTransaction()` not `addToQueueAndWait()`.
- **Use Standard Nomenclature**: Adopt conventional terms from patterns or domains (e.g., `Visitor` for Visitor pattern).  
  *Example*: `AccountVisitor` for a class implementing the Visitor pattern.
- **Scale Length with Scope**: Short names (e.g., `i` for loops) are fine in small scopes (5-10 lines); use longer names in larger scopes or global contexts.
- **Avoid Encodings**: Do not prefix with type (e.g., Hungarian notation like `strName`) or scope (e.g., `m_member`). Modern IDEs handle this.

## Directory and File Naming
- **Use Consistent Casing and Style**: Adopt a uniform convention like kebab-case for files (e.g., `user-service.ts`) or snake_case (e.g., `user_service.py`), based on language standards (e.g., PEP8 for Python). Avoid mixing styles.  
  *Bad*: `UserService.Ts` (inconsistent capitalization).  
  *Good*: `user-service.ts` (kebab-case, descriptive).
- **Be Descriptive and Specific**: Directory and file names should reveal their contents' purpose without needing to open them. Use domain-specific terms.  
  *Example*: `auth-controller.ts` instead of `ctrl1.ts`.
- **Prefer Singular Names for Directories**: Use singular forms for folders to indicate they contain related items (e.g., `controller` not `controllers`). For files, use singular unless representing collections.  
  *Bad*: `users/` (plural implying single entity).  
  *Good*: `user/` (singular, contains user-related files).
- **Organize by Responsibility and Layers**: Structure directories to reflect architectural layers, promoting single responsibility (e.g., `src/controllers`, `src/services`, `src/models`, `src/repositories`, `src/utils`). Include top-level folders like `tests`, `config`, `docs`.  
  *Example*: In a backend, group persistence logic under `repositories/user-repository.go`.
- **Avoid Deep Nesting and Ambiguity**: Limit directory depth to 3-4 levels; use flat structures where possible. Avoid vague names like `stuff` or `misc`; refactor as needed.  
  *Bad*: `src/stuff/user/things`.  
  *Good*: `src/user/service`.
- **Align with Domain and Standards**: Use plural for database-related names (e.g., `user_accounts` table). Follow language/framework conventions for modularity and scalability.

## General Naming Principles (to Avoid Comments and Smells)
- **Prefer Names Over Comments**: Refactor code to use self-explanatory names for functions/variables instead of comments.  
  *Bad*: `// Check if employee is eligible for full benefits if ((employee.flags & HOURLY_FLAG) && (employee.age > 65))`.  
  *Good*: `if (employee.isEligibleForFullBenefits())`.
- **Ensure Names Describe Everything**: Names should cover all behaviors and side effects to prevent misleading readers.
- **Maintain Consistency**: Pick one word per abstract concept and stick with it (e.g., use `fetch` everywhere, not mixing with `get` or `retrieve`).

## Application
Apply these rules during refactoring and TDD. Good naming reduces the need for comments, improves code navigation, and minimizes bugs from misunderstandings. Review names frequently as code changes, extending to directory structures for overall codebase cleanliness.