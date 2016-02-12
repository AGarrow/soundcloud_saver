on run argv
  set sc_playlist to item 1 of argv
  set track_filepath to item 2 of argv as POSIX file
  set track_name to item 3 of argv
  
  log track_filepath

  tell application "iTunes"
    
    if not (exists playlist sc_playlist) then
      make new playlist at folder playlist sc_user with properties{name:sc_playlist}
    end if
    
    set track_id to add track_filepath
    
    if not exists (track track_name of playlist sc_playlist) then
      copy track_id to end of user playlist sc_playlist
    end
  end tell
end run