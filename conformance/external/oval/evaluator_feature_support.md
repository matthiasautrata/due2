# ODRL 2.2 Feature Support for the OVAL Evaluator

Summary of what the OVAL evaluator supports:
* All policy types
* All rule types
* Any domain-specific vocabulary
* Reasoning over includedIn and partOf
* Compact ODRL policy format (rule components defined at the policy level)
* Constraints and refinements over IDs, strings, dates and sets
* Full support for the special semantics of the `count` Left Operand
* Support for ODRL `conflict` strategy within the Access Control mode
* Support for configurable semantics in the Access control mode, including different semantics for duties, and permission-by-default / prohibition-by-default / unspecified-by-default semantics 
* Nested Logic Constraints of arbitrary complexity

Summary of what the OVAL Evaluator does not support yet:
* Special semantics of certain Left Operands, like those about spatial data


### Core Policy Feature Support

| Feature name                                                                 | Supported | Notes                                                                                                                                 | Tests |
|------------------------------------------------------------------------------|-----------|---------------------------------------------------------------------------------------------------------------------------------------|-|
| [Policy](http://www.w3.org/ns/odrl/2/Policy)                                 | 🟢 Yes    |                                                                                                                                       | ✓|
| [Set](http://www.w3.org/ns/odrl/2/Set)                                       | 🟢 Yes    |                                                                                                                                       | ✓|
| [Offer](http://www.w3.org/ns/odrl/2/Offer)                                   | 🟢 Yes    |                                                                                                                                       | ✓|
| [Agreement](http://www.w3.org/ns/odrl/2/Agreement)                           | 🟢 Yes    |                                                                                                                                       | ✓|
| [Profile](http://www.w3.org/ns/odrl/2/profile)                               | 🟡        | The evaluator natively supports any domain specific terminology, without requiring explicit profile specifications.                   | |
| [Permission](http://www.w3.org/ns/odrl/2/Permission)                         | 🟢 Yes    |                                                                                                                                       | ✓|
| [Prohibition](http://www.w3.org/ns/odrl/2/Prohibition)                       | 🟢 Yes    |                                                                                                                                       | ✓|
| [Duty](http://www.w3.org/ns/odrl/2/Duty)                                     | 🟢 Yes    |                                                                                                                                       | ✓|
| [Obligation](http://www.w3.org/ns/odrl/2/obligation)                         | 🟢 Yes    |                                                                                                                                       | ✓|
| [Target](http://www.w3.org/ns/odrl/2/target)                                 | 🟢 Yes    |                                                                                                                                       | ✓|
| [Assigner](http://www.w3.org/ns/odrl/2/assigner)                             | 🟡        | Not relevant to the evaluation semantics.                                                                                             | |
| [Assignee](http://www.w3.org/ns/odrl/2/assignee)                             | 🟢 Yes    |                                                                                                                                       | ✓|
| [Asset](http://www.w3.org/ns/odrl/2/Asset)                                   | 🟢 Yes    |                                                                                                                                       | ✓|
| [Asset Collection](http://www.w3.org/ns/odrl/2/AssetCollection)              | 🟢 Yes    |                                                                                                                                       | ✓|
| [Party](http://www.w3.org/ns/odrl/2/Party)                                   | 🟢 Yes    |                                                                                                                                       | ✓|
| [Party Collection](http://www.w3.org/ns/odrl/2/PartyCollection)              | 🟢 Yes    |                                                                                                                                       | ✓|
| [Collection Parts (partOf)](http://www.w3.org/ns/odrl/2/partOf)              | 🟢 Yes     |                                                                                                                                       | ✓|
| [Action](http://www.w3.org/ns/odrl/2/Action)                                 | 🟢 Yes    |                                                                                                                                       | ✓|
| [Action Inclusion (includedIn)](http://www.w3.org/ns/odrl/2/includedIn)      | 🟢 Yes     |                                                                                                                                       | ✓|
| [Action Implies](http://www.w3.org/ns/odrl/2/implies)                        | 🔴 No     |                                                                                                                                       | |
| [Action Refinement](http://www.w3.org/ns/odrl/2/refinement)                  | 🟢 Yes    |                                                                                                                                       | ✓|
| [Asset Collection Refinement](http://www.w3.org/ns/odrl/2/refinement)        | 🟢 Yes    |                                                                                                                                       |✓ |
| [Party Collection Refinement](http://www.w3.org/ns/odrl/2/refinement)        | 🟢 Yes    |                                                                                                                                       | ✓|
| [Constraint](http://www.w3.org/ns/odrl/2/Constraint)                         | 🟢 Yes    |                                                                                                                                       | ✓|
| [Logical Constraint](http://www.w3.org/ns/odrl/2/LogicalConstraint)          | 🟢 Yes    |                                                                                                                                       | ✓|
| [Left Operand](http://www.w3.org/ns/odrl/2/leftOperand)                      | 🟢 Yes    |                                                                                                                                       | ✓|
| [Right Operand](http://www.w3.org/ns/odrl/2/rightOperand)                    | 🟢 Yes    |                                                                                                                                       | ✓|
| [Right Operand Reference](http://www.w3.org/ns/odrl/2/rightOperandReference) | 🔴 No     |                                                                                                                                       | |
| [Data Type](http://www.w3.org/ns/odrl/2/dataType)                            | 🔴 No     |                                                                                                                                       | |
| [Unit](http://www.w3.org/ns/odrl/2/unit)                                     | 🔴 No     |                                                                                                                                       | |
| [Status](http://www.w3.org/ns/odrl/2/status)                                 | 🔴 No     |                                                                                                                                       | |
| [Operator](http://www.w3.org/ns/odrl/2/Operator)                             | 🟢 Yes    |                                                                                                                                       | ✓|
| [Equal To](http://www.w3.org/ns/odrl/2/eq)                                   | 🟢 Yes    |                                                                                                                                       | ✓|
| [Not Equal To](http://www.w3.org/ns/odrl/2/neq)                              | 🟢 Yes    |                                                                                                                                       | |
| [Less Than](http://www.w3.org/ns/odrl/2/lt)                                  | 🟢 Yes    |                                                                                                                                       | ✓|
| [Less Than or Equal To](http://www.w3.org/ns/odrl/2/lteq)                    | 🟢 Yes    |                                                                                                                                       | ✓|
| [Greater Than](http://www.w3.org/ns/odrl/2/gt)                               | 🟢 Yes    |                                                                                                                                       | ✓|
| [Greater Than or Equal To](http://www.w3.org/ns/odrl/2/gteq)                 | 🟢 Yes    |                                                                                                                                       | ✓|
| [Is A](http://www.w3.org/ns/odrl/2/isA)                                      | 🔴 No     |                                                                                                                                       | |
| [Is All Of](http://www.w3.org/ns/odrl/2/isAllOf)                             | 🟢 Yes     |                                                                                                                                       |✓ |
| [Is Any Of](http://www.w3.org/ns/odrl/2/isAnyOf)                             | 🟢 Yes     |                                                                                                                                       | ✓|
| [Is None Of](http://www.w3.org/ns/odrl/2/isNoneOf)                           | 🟢 Yes     |                                                                                                                                       |✓ |
| [Is Part Of](http://www.w3.org/ns/odrl/2/isPartOf)                           | 🟢 Yes     |                                                                                                                                       | ✓|
| [Has Part](http://www.w3.org/ns/odrl/2/hasPart)                              | 🟢 Yes     |                                                                                                                                       | ✓|
| [OR](http://www.w3.org/ns/odrl/2/or)                                         | 🟢 Yes    |                                                                                                                                       | ✓|
| [XONE](http://www.w3.org/ns/odrl/2/xone)                                     | 🟢 Yes    |                                                                                                                                       | ✓|
| [AND](http://www.w3.org/ns/odrl/2/and)                                       | 🟢 Yes    |                                                                                                                                       | ✓|
| [AND Sequence](http://www.w3.org/ns/odrl/2/andSequence)                      | 🟡        | Interpreted as a simple AND, as the sequence of evaluation does not affect the evaluation semantics used.                             | |
| [Permission Duty](http://www.w3.org/ns/odrl/2/duty)                          | 🟢 Yes    |                                                                                                                                       | ✓|
| [Duty Consequence](http://www.w3.org/ns/odrl/2/consequence)                  | 🟢 Yes    |                                                                                                                                       | ✓|
| [Prohibition Remedy](http://www.w3.org/ns/odrl/2/remedy)                     | 🟢 Yes    |                                                                                                                                       | ✓|
| [Policy Inheritance](http://www.w3.org/ns/odrl/2/inheritFrom)                | 🔴 No     |                                                                                                                                       | |
| [Conflict Strategy](http://www.w3.org/ns/odrl/2/conflict)                    | 🟢 Yes / 🔴 No | Fully supported in Access Control mode, not supported in Monitoring mode (currently defaults to prohibitions overriding permissions). | | | |

### Left Operand Support

Left operand evaluation involves comparing the value of a left operand in an event in the State of the World
with the value of the right operand of a constraint/refinement, based on the given operator.

#### Default Behaviour

The evalutor is domain-agnostic, and can process any domain specific Left Operand from any ontology. 
The evaluator currently supports comparison of dates, numbers and string and URI identifiers in the State of the World object. 
The default behaviour for a generic Left Operand is as follows. 
Values are considered strings/URIs by default if using the equality operator, or numbers if using a numerical comparison operator like < or >=, unless a common date format (like %d-%m-%Y, %Y-%m-%d, %Y-%m-%dT%H:%M:%S, %Y-%m-%dT%H:%M) is detected. This means that for numbers to be considered equal, they need to be written in the same syntactic form (e.g. '4' would not be considered equal to '4.0').

#### Special Left Operand Support

Certain Left Operands require a different approach of evaluation than the one listed above, and the table below summarises the current support for
these special cases. 
* Left operands marked as "🟢 Yes" mean that a special support for the Left Operand has been implemented and overrides the default
behaviour listed above. 
* Left operands marked with "🟡" mean that no special support for the Left Operand is needed. They are processed according
to the default behaviour, and this behaviour is deemed to be sufficient in most cases.
* Left operands marked as "🔴 No" mean that special support for the Left Operand is needed but not currently implemented. 
They will still be processed by the evaluator, but according to the default
behaviour listed above which might not have the intededed effect. 

| Feature name | Implemented | Notes | Tests |
|---|---|---|---|
| [absolutePosition](https://www.w3.org/ns/odrl/2/absolutePosition) | 🔴 No | | |
| [absoluteSize](https://www.w3.org/ns/odrl/2/absoluteSize) | 🔴 No | | |
| [absoluteSpatialPosition](https://www.w3.org/ns/odrl/2/absoluteSpatialPosition) | 🔴 No | | |
| [absoluteTemporalPosition](https://www.w3.org/ns/odrl/2/absoluteTemporalPosition) | 🟡 | | |
| [count](https://www.w3.org/ns/odrl/2/count) | 🟢 Yes | | ✓|
| [dateTime](https://www.w3.org/ns/odrl/2/dateTime) | 🟢 Yes | | ✓|
| [delayPeriod](https://www.w3.org/ns/odrl/2/delayPeriod) | 🔴 No | | |
| [deliveryChannel](https://www.w3.org/ns/odrl/2/deliveryChannel) | 🟡 | | |
| [device](https://www.w3.org/ns/odrl/2/device) | 🟡 | | |
| [elapsedTime](https://www.w3.org/ns/odrl/2/elapsedTime) | 🔴 No | | |
| [event](https://www.w3.org/ns/odrl/2/event) | 🟡 | | |
| [fileFormat](https://www.w3.org/ns/odrl/2/fileFormat) | 🟡 | | |
| [industry](https://www.w3.org/ns/odrl/2/industry) | 🟡 | | |
| [language](https://www.w3.org/ns/odrl/2/language) | 🟡 | | |
| [media](https://www.w3.org/ns/odrl/2/media) | 🟡 | | |
| [meteredTime](https://www.w3.org/ns/odrl/2/meteredTime) | 🔴 No | | |
| [payAmount](https://www.w3.org/ns/odrl/2/payAmount) | 🟡 | | |
| [percentage](https://www.w3.org/ns/odrl/2/percentage) | 🟡 | | |
| [product](https://www.w3.org/ns/odrl/2/product) | 🟡 | | |
| [purpose](https://www.w3.org/ns/odrl/2/purpose) | 🟡 | | |
| [recipient](https://www.w3.org/ns/odrl/2/recipient) | 🟡 | | |
| [relativePosition](https://www.w3.org/ns/odrl/2/relativePosition) | 🔴 No | | |
| [relativeSize](https://www.w3.org/ns/odrl/2/relativeSize) | 🔴 No | | |
| [relativeSpatialPosition](https://www.w3.org/ns/odrl/2/relativeSpatialPosition) | 🔴 No | | |
| [relativeTemporalPosition](https://www.w3.org/ns/odrl/2/relativeTemporalPosition) | 🔴 No | | |
| [resolution](https://www.w3.org/ns/odrl/2/resolution) | 🟡 | | |
| [spatial](https://www.w3.org/ns/odrl/2/spatial) | 🔴 No | | |
| [spatialCoordinates](https://www.w3.org/ns/odrl/2/spatialCoordinates) | 🔴 No | | |
| [system](https://www.w3.org/ns/odrl/2/system) |🟡 | | |
| [systemDevice](https://www.w3.org/ns/odrl/2/systemDevice) | 🟡 | | |
| [timeInterval](https://www.w3.org/ns/odrl/2/timeInterval) | 🔴 No | | |
| [unitOfCount](https://www.w3.org/ns/odrl/2/unitOfCount) | 🔴 No | | |
| [version](https://www.w3.org/ns/odrl/2/version) | 🟡 | | |
| [virtualLocation](https://www.w3.org/ns/odrl/2/virtualLocation) | 🟡 | | |