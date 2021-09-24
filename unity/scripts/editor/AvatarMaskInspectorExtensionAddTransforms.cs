/*
Note that this script replaces the default GUI for AvatarMasks.
A less invasive script for more general use could have its own GUI where an AvatarMask and GameObject can be specified.
This script also uses Reflection, so could break with Unity updates in the future. The script has been tested on 2019.4.29f1.

This is also my first script for Unity so there could be things that are wrong or weird, but it seems to work ok.

Remember to make sure this script is within a folder called Editor, otherwise Unity will try to compile it when attempting to upload a VRChat
avatar and the compilation will fail, preventing you from uploading.

-----------------------

If you add a GameObject to an avatar and want to use that GameObject within an AvatarMask, Unity gives no easy way to easily do so.
The only way to add Transforms to an AvatarMask is:
  through a Skeleton defined in an Avatar Object,
  manually in the debug Inspector,
  with scripts
The suggestions I've seen online for including extra added GameObjects is to either add them in Blender
or to export the entire avatar with extra GameObjects included as an FBX and import that new FBX into Unity,
both of which are ludicrous to me.

This script adds an extra input field and button to the bottom of the Transform section of the AvatarMask UI
You can specify a GameObject and import the transforms from its hierarchy by pressing the button
!!! Make sure the GameObject you're importing from has no parent object in the scene, otherwise its parent objects will be included in the transform paths !!!
Currently, this will replace all transforms in the mask, the same behaviour as importing from a skeleton
TODO: It would be nice to add some extra options, such as keeping existing transforms and their active state if they exist in the transforms being imported
*/
using UnityEngine;
using UnityEditor;
using System.Reflection;
using System;

namespace Mysteryem.CustomEditors {
    [CustomEditor(typeof(AvatarMask), true)]
    public class AvatarMaskInspectorExtensionAddTransforms : Editor {
        // Unity's built-in editor
        private Editor defaultEditor;
        private AvatarMask avatarMask;
        
        // Transform Mask Foldout field of Unit's built-in editor
        private FieldInfo transformFoldoutField;
        
        void OnEnable() {
            // Default editor code from https://forum.unity.com/threads/extending-instead-of-replacing-built-in-inspectors.407612/
            defaultEditor = Editor.CreateEditor(targets, System.Type.GetType("UnityEditor.AvatarMaskInspector, UnityEditor"));
            avatarMask = target as AvatarMask;
            // Get the FieldInfo for the Transform Mask Foldout since the field is private
            transformFoldoutField = defaultEditor.GetType().GetField("m_TransformMaskFoldout", BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.DeclaredOnly);
        }
        
        void OnDisable() {
            // OnDisable is not called for the default editor as it is apparently called automatically on destruction
            // Destroy the default editor we created to avoid memory leakage, not sure if this is
            DestroyImmediate(defaultEditor);
        }
        
        private GameObject transformSource;
        
        public override void OnInspectorGUI() {
            defaultEditor.OnInspectorGUI();
            
            Boolean transformFoldoutOpen = (Boolean)transformFoldoutField.GetValue(defaultEditor);
            
            if (transformFoldoutOpen) {
                // Add a little label to describe what this does and point out that it's custom
                GUILayout.Label("Custom transform importer for Game Objects", EditorStyles.wordWrappedMiniLabel);
                
                // Get the GameObject the transforms will be added from
                transformSource = EditorGUILayout.ObjectField("Use transforms from", transformSource, typeof(GameObject), true) as GameObject;
                
                using (new EditorGUI.DisabledScope(transformSource == null)) {            
                  if ((Boolean)GUILayout.Button("Import transforms from Game Object")) {
                      if (transformSource != null) {
                          // Setting the transformCount to zero seems to work well in clearing all the current transforms
                          avatarMask.transformCount = 0;
                          avatarMask.AddTransformPath(transformSource.transform);
                          Debug.Log("Imported transforms recursively from " + transformSource.transform);
                      }
                  }
                }
            }
        }
    }
}
