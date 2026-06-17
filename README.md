# CenBlender
Blender addons that are used to develop The Pact of Centradigon.

Blender's python API (bpy) is very low level. This may be great for those developing complex addons that truly extend what Blender is capable of, but for those who just want to write some python code to automate what they would otherwise be doing by hand, it's a pain. It's like writing assembly language where the syntax is still python-like. 

The addons in this repository are generally automations of what I had done by hand before. As such, they depend on basic functionality like duplicating objects, deactivating collections, adding and editing modifiers, selecting objects, etc. But of course, Blender doesn't provide a user-friendly interface to access this stuff. 

The file CenLib.py contains a list of functions that intend to solve this. Many one-click operations from the UI are instead represented with rather peculiar chains of different operations, often involving recursion, highlighting just how low level bpy truly is. Sometimes an action seems to be represented by a single line of code, but when doing things that way it can lead to a UI that is out of sync with what is happening behind the scenes. In cases where an operation is truly represented with a single line, it's still very hard to remember the exact name of whatever property is required to be edited or read to make use of it. As such, even these operations are given clearly named functions. If I spend a few weeks working in Unity and suddenly need to make another Blender addon to automate some process, I don't need to re-learn the entire Blender API and all of its quirks, but rather I can just open CenLib on the side, and search for and use all of the high level functions that are necessary to solve the actual problem at hand.

With CenLib, writing addons is basically as seamless as writing editor scripts in Unity. However, almost all of the addons in this repository were written before this library existed. Thus, a lot of them are currently needlessly complex and fragile. As time goes on, I'll try to update all of them to rely entirely on CenLib, such that each of them can be independently read, understood, and that it can be easily verified that they are working as intended. I'll also expand CenLib with whatever other functionality I need for future addons.

If an operation can be clearly named, it will probably end up in CenLib.


# How to Install
Download all of the .py files. Open Blender. Edit -> Preferences -> Addons -> Arrow button in top right -> Install from disk, for all .py files.
