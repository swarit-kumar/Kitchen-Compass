# KitchenCompass professor demo

Allow about five minutes. Complete the Windows setup in [README.md](../README.md) before class, run the tests once, and open the app. After installation the demonstration uses packaged local data. The numbers below were reproduced on checkpoint P03 v0.4.

| Screen | What to do | What to point out |
|---|---|---|
| Pantry search | Keep `potato, tomato, onion, water`, exclude `milk`, select **Weighted match**, click **Find recipes**. Switch to **Simple overlap** and search again. | Weighted match puts Aloo Matar first. Simple overlap puts Japanese Chicken Curry first. Open the match list to show the available and missing ingredients. Milk and its known derivatives were filtered before ranking. |
| Substitutions | Click **Paneer masala**, then **Find substitutes**. | The target is paneer. The pantry has firm tofu, silken tofu and cheddar. A milk exclusion removes cheddar even though it is available. Firm tofu scores 0.596 and silken tofu 0.497. Both use protein role and recipe context. The screen identifies the missing molecular profiles. |
| Substitutions | Click **Flavor comparison**, then **Find substitutes**. Change **Substitution method** to **Flavor only** and run again. | The target is garlic in Lemon Coriander Soup. The full model returns onion at 0.756. Flavor alone returns onion, potato and tomato. Garlic and onion share 120 of 203 distinct measured compounds. Potato and tomato lack the matching aromatic role for the full model. |
| Substitutions | Click **Instruction match**, then **Find substitutes**. | Broccoli Cheddar Soup calls for stirring in flour. The app shows the matched sentence and the `roux_thickener` rule. Cornstarch scores 0.547 as a thickener using role and context. The cook still decides how to adjust preparation. |
| Substitutions | Click **Impossible pantry**, then **Find substitutes**. Expand **Why candidates were filtered**. | Cheddar is the only pantry candidate. Its milk component conflicts with the exclusion, so the app returns an empty list. |
| Custom recipes | Paste the sample below, click **Review ingredients**, select **onion** for the first line and click **Save custom recipe**. Use **Download recipe JSON**, then **Use this recipe for substitution**. | The original phrase and quantity survive confirmation. Select **onion** as target, add **garlic** to the pantry, check the pantry-only box and run. Garlic appears. Opening a new browser session gives an empty custom list. Import the downloaded JSON there to restore the recipe. |

### Custom recipe to paste

Title: `My onion and potato soup`

Ingredients (one per line)

```text
finely sliced onion | 1 small
aloo | 1
```

Instructions (one per line)

```text
Soften the onion.
Add potato and simmer.
```

### If the professor asks about evaluation

The context model uses 124 training recipes. The six existing single-substitution development cases are held outside that training split. The full method returned suggestions for six and the flavor-only method for zero. The flavor comparison above is a separate demonstration using available profiles. Only five ingredients currently have measured molecular profiles. The team still needs to grade the development options before reporting ranking accuracy. Multi-ingredient replacement is the next phase.
