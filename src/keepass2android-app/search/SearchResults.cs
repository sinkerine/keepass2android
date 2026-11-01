/*
This file is part of Keepass2Android, Copyright 2013 Philipp Crocoll. This file is based on Keepassdroid, Copyright Brian Pellin.

  Keepass2Android is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  Keepass2Android is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with Keepass2Android.  If not, see <http://www.gnu.org/licenses/>.
  */
using System;
using System.Linq;
using Android.App;
using Android.Content;
using Android.Content.PM;
using Android.OS;
using Android.Preferences;
using Android.Views;
using Android.Widget;
using AndroidX.Core.Content;
using AndroidX.Lifecycle;
using keepass2android.view;
using keepass2android;
using KeePassLib;

namespace keepass2android.search
{
  /// <summary>
  /// Activity to show search results
  /// </summary>
  [Activity(Label = "@string/app_name", Theme = "@style/Kp2aTheme_ActionBar", LaunchMode = Android.Content.PM.LaunchMode.SingleTop, Permission = "keepass2android." + AppNames.PackagePart + ".permission.KP2aInternalSearch", ConfigurationChanges = ConfigChanges.Orientation | ConfigChanges.Keyboard | ConfigChanges.KeyboardHidden, Exported = true)]
#if NoNet
    [MetaData("android.app.searchable", Resource = "@xml/searchable_offline")]
#else
#if DEBUG
  [MetaData("android.app.searchable", Resource = "@xml/searchable_debug")]
#else
    [MetaData("android.app.searchable", Resource = "@xml/searchable")]
#endif
#endif
  [MetaData("android.app.default_searchable", Value = "keepass2android.search.SearchResults")]
  [IntentFilter(new[] { Intent.ActionSearch }, Categories = new[] { Intent.CategoryDefault })]
  public class SearchResults : GroupBaseActivity
  {
    private bool _readLockAcquired;
    private SearchSyncHandoff _syncHandoff;

    protected override void OnCreate(Bundle bundle)
    {
      // The temporary group contains live entries: keep the reader until its UI is destroyed.
      _readLockAcquired = App.Kp2a.DatabasesBackgroundModificationLock.TryEnterReadLock(TimeSpan.FromSeconds(5));
      if (!_readLockAcquired)
        Finish();

      // Android requires base creation even when lock acquisition fails. GroupBaseActivity
      // skips initializing the list when this activity is already finishing.
      base.OnCreate(bundle);
      if (!_readLockAcquired)
      {
        App.Kp2a.ShowMessage(this, GetString(Resource.String.failed_to_access_database), MessageSeverity.Error);
        return;
      }

      if (IsFinishing)
      {
        return;
      }

      SetResult(KeePass.ExitNormal);

      ProcessIntent(Intent);
    }

    protected override void OnDestroy()
    {
      try
      {
        base.OnDestroy();
      }
      finally
      {
        if (_readLockAcquired)
        {
          App.Kp2a.DatabasesBackgroundModificationLock.ExitReadLock();
          _readLockAcquired = false;
        }
        var handoff = _syncHandoff;
        _syncHandoff = null;
        handoff?.OnReaderReleased();
      }
    }

    protected override void SynchronizeCurrentDatabase()
    {
      if (_syncHandoff != null || IsFinishing || !_readLockAcquired)
        return;

      var database = App.Kp2a.CurrentDb;
      if (!App.Kp2a.DatabaseIsUnlocked || database == null || !App.Kp2a.OpenDatabases.Contains(database))
        return;

      _syncHandoff = new SearchSyncHandoff(Application, database);
      AppTask.SetActivityResult(this, KeePass.ExitNormal);
      Finish();
    }

    // Neither OnResume nor OnDestroy is guaranteed to happen first during a return.
    // Observe both, and enqueue once only after destruction has released the reader.
    private sealed class SearchSyncHandoff : BroadcastReceiver, Application.IActivityLifecycleCallbacks, ILifecycleEventObserver
    {
      private readonly Application _application;
      private Database _database;
      private bool _readerReleased;

      public SearchSyncHandoff(Application application, Database database)
      {
        _application = application;
        _database = database;
        _application.RegisterActivityLifecycleCallbacks(this);
        ContextCompat.RegisterReceiver(_application, this, new IntentFilter(Intents.DatabaseLocked), (int)ReceiverFlags.NotExported);
        ProcessLifecycleOwner.Get().Lifecycle.AddObserver(this);
      }

      public void OnReaderReleased()
      {
        _readerReleased = true;
        PostTrySynchronize();
      }

      private void PostTrySynchronize()
      {
        // Post past the complete activity callback, including timeout checks and UI setup.
        App.Kp2a.UiThreadHandler.Post(TrySynchronize);
      }

      private void TrySynchronize()
      {
        if (_database == null)
          return;
        if (!App.Kp2a.DatabaseIsUnlocked || !App.Kp2a.OpenDatabases.Any(db => ReferenceEquals(db, _database)))
        {
          Cancel();
          return;
        }
        if (!_readerReleased || App.Kp2a.ActiveContext is not LifecycleAwareActivity activity ||
            activity is SearchResults || activity.IsFinishing || activity.IsDestroyed ||
            !activity.Lifecycle.CurrentState.IsAtLeast(Lifecycle.State.Resumed))
          return;

        var database = _database;
        Cancel();
        new SyncUtil(activity).StartSynchronizeDatabase(database, true);
      }

      private void Cancel()
      {
        if (_database == null)
          return;
        _database = null;
        _application.UnregisterActivityLifecycleCallbacks(this);
        _application.UnregisterReceiver(this);
        ProcessLifecycleOwner.Get().Lifecycle.RemoveObserver(this);
      }

      public override void OnReceive(Context context, Intent intent) => Cancel();
      public void OnStateChanged(ILifecycleOwner source, Lifecycle.Event lifecycleEvent)
      {
        // Do not retain a user request across backgrounding/locking the app.
        if (lifecycleEvent == Lifecycle.Event.OnStop)
          Cancel();
      }
      public void OnActivityResumed(Activity activity) => PostTrySynchronize();
      public void OnActivityDestroyed(Activity activity) => PostTrySynchronize();
      public void OnActivityCreated(Activity activity, Bundle savedInstanceState) { }
      public void OnActivityStarted(Activity activity) { }
      public void OnActivityPaused(Activity activity) { }
      public void OnActivityStopped(Activity activity) { }
      public void OnActivitySaveInstanceState(Activity activity, Bundle outState) { }
    }

    public override bool EntriesBelongToCurrentDatabaseOnly
    {
      get { return false; }
    }

    public override ElementAndDatabaseId FullGroupId
    {
      get { return null; }
    }


    protected override void OnNewIntent(Intent intent)
    {
      if (IsFinishing || !_readLockAcquired || _syncHandoff != null)
        return;
      ProcessIntent(intent);
    }

    private void ProcessIntent(Intent intent)
    {
      // Likely the app has been killed exit the activity 
      if (!App.Kp2a.DatabaseIsUnlocked)
      {
        Finish();
        return;
      }

      if (intent.Action == Intent.ActionView)
      {
        var entryIntent = new Intent(this, typeof(EntryActivity));
        ElementAndDatabaseId id;
        try
        {
          id = new ElementAndDatabaseId(intent.Data.LastPathSegment);
        }
        catch (Exception e)
        {
          Kp2aLog.Log("Failed to transform " + intent.Data.LastPathSegment + " to an ElementAndDatabaseId object. ");
          App.Kp2a.ShowMessage(this, "Bad path passed. Please provide database and element ID.", MessageSeverity.Error);
          Finish();
          return;
        }
        entryIntent.PutExtra(EntryActivity.KeyEntry, id.FullId);
        entryIntent.AddFlags(ActivityFlags.ForwardResult);
        Finish(); // Close this activity so that the entry activity is navigated to from the main activity, not this one.
        StartActivity(entryIntent);

      }
      else
      {
        // Action may either by ActionSearch (from search widget) or null (if called from SearchActivity directly)
        Query(getSearch(intent));
      }
    }

    private void Query(SearchParameters searchParams)
    {
      //kind of an easter egg: if the user types this exact string into the search, it immediately allows to disable the donation options
      if (searchParams.SearchString == "allow disable donation")
      {
        ISharedPreferences prefs = PreferenceManager.GetDefaultSharedPreferences(this);
        ISharedPreferencesEditor edit = prefs.Edit();
        edit.PutLong(GetString(Resource.String.UsageCount_key), 1000);
        edit.PutBoolean("DismissedDonateReminder", true);
        edit.Commit();
        App.Kp2a.ShowMessage(this, "Please go to Settings - App - Display to disable donation requests.", MessageSeverity.Error);
      }


      Group = null;
      try
      {
        foreach (var db in App.Kp2a.OpenDatabases)
        {
          PwGroup resultsForThisDb = db.Search(searchParams, null);
          if (Group == null)
            Group = resultsForThisDb;
          else
          {
            foreach (var entry in resultsForThisDb.Entries)
            {
              Group.AddEntry(entry, false);
            }
          }
        }
      }
      catch (Exception e)
      {
        Kp2aLog.LogUnexpectedError(e);
        App.Kp2a.ShowMessage(this, Util.GetErrorMessage(e), MessageSeverity.Error);
        Finish();
        return;
      }

      if (Group == null || (!Group.Entries.Any()))
      {
        SetContentView(Resource.Layout.group_empty);
      }

      SetGroupTitle();

      FragmentManager.FindFragmentById<GroupListFragment>(Resource.Id.list_fragment).ListAdapter = new PwGroupListAdapter(this, Group);
    }

    private SearchParameters getSearch(Intent queryIntent)
    {
      // get and process search query here
      SearchParameters sp = new SearchParameters();
      sp.SearchString = queryIntent.GetStringExtra(SearchManager.Query);
      sp.SearchInTitles = queryIntent.GetBooleanExtra("SearchInTitles", sp.SearchInTitles);
      sp.SearchInUrls = queryIntent.GetBooleanExtra("SearchInUrls", sp.SearchInUrls);
      sp.SearchInPasswords = queryIntent.GetBooleanExtra("SearchInPasswords", sp.SearchInPasswords);
      sp.SearchInUserNames = queryIntent.GetBooleanExtra("SearchInUserNames", sp.SearchInUserNames);
      sp.SearchInNotes = queryIntent.GetBooleanExtra("SearchInNotes", sp.SearchInNotes);
      sp.SearchInGroupNames = queryIntent.GetBooleanExtra("SearchInGroupNames", sp.SearchInGroupNames);
      sp.SearchInOther = queryIntent.GetBooleanExtra("SearchInOther", sp.SearchInOther);
      sp.SearchInTags = queryIntent.GetBooleanExtra("SearchInTags", sp.SearchInTags);
      sp.RegularExpression = queryIntent.GetBooleanExtra("RegularExpression", sp.RegularExpression);
      sp.ExcludeExpired = queryIntent.GetBooleanExtra("ExcludeExpired", sp.ExcludeExpired);
      sp.ComparisonMode = queryIntent.GetBooleanExtra("CaseSensitive", false) ?
          StringComparison.InvariantCulture :
              StringComparison.InvariantCultureIgnoreCase;

      return sp;

    }

    public override void OnCreateContextMenu(IContextMenu menu, View v,
        IContextMenuContextMenuInfo menuInfo)
    {

      AdapterView.AdapterContextMenuInfo acmi = (AdapterView.AdapterContextMenuInfo)menuInfo;
      ClickView cv = (ClickView)acmi.TargetView;
      cv.OnCreateMenu(menu, menuInfo);
    }

    public override bool OnContextItemSelected(IMenuItem item)
    {
      AdapterView.AdapterContextMenuInfo acmi = (AdapterView.AdapterContextMenuInfo)item.MenuInfo;
      ClickView cv = (ClickView)acmi.TargetView;

      bool result;

      return cv.OnContextItemSelected(item);
    }


    public override bool OnSearchRequested()
    {
      Intent i = new Intent(this, typeof(SearchActivity));
      this.AppTask.ToIntent(i);
      i.SetFlags(ActivityFlags.ForwardResult);
      StartActivity(i);
      return true;
    }

    public override bool IsSearchResult
    {
      get { return true; }
    }
  }
}

