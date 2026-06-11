# Momentum: Figma AI Design Brief

## Product Overview

Momentum is a responsive social productivity application that combines task
management, analytics, social accountability, XP progression, quests, streaks,
and achievements.

The core product loop is:

> Plan a task, complete it, earn XP, progress quests and badges, optionally
> share the completion, and receive social encouragement.

The intended audience includes students and young professionals. The interface
should feel focused, mature, motivating, and efficient rather than like a
colorful mobile game or generic SaaS landing page.

## Visual Direction

- Quiet, productivity-focused visual language.
- Light gray-green application background.
- White surfaces with restrained borders and subtle shadows.
- Dark teal navigation.
- Green for primary actions, progress, and completion.
- Gold for focus, XP, streaks, and achievements.
- Coral or red for overdue, destructive, and warning states.
- Blue for informational and low-priority states.
- Maximum card radius of approximately 8px.
- Compact typography suitable for an operational application.
- Dense but readable layouts with strong visual hierarchy.
- Lucide-style line icons.
- Avoid gradients, decorative blobs, oversized marketing sections, and nested
  cards.

## Responsive Frames

Create designs for these representative viewport widths:

- Desktop: 1440px.
- Compact laptop: approximately 1180px.
- Tablet: approximately 820px.
- Mobile: approximately 390px.

### Desktop

- Fixed dark sidebar with full navigation labels.
- Constrained central content area.
- Multi-column page layouts where appropriate.

### Tablet

- Compact icon-only navigation rail.
- Content reorganized into fewer columns.
- Forms wrap into intentional rows.
- Side panels move below primary content when necessary.

### Mobile

- Dark sticky top application bar.
- Fixed bottom navigation with five destinations.
- Single-column content.
- Full-width forms and primary actions.
- Thumb-friendly controls.
- No horizontal page scrolling.
- Secondary task actions wrap beneath task content.

## Application Shell

### Branding

- Product name: **Momentum**.
- Subtitle: **Productivity network**.
- Brand icon: checkmark inside a rounded square.

### Primary Navigation

1. Today
2. Tasks
3. Social
4. Gamification / Progress
5. Statistics

Use **Gamification** on desktop and the shorter **Progress** label on mobile.

### Account Area

- Initial-based avatar.
- Display name.
- Email address.
- Icon-only logout button with a tooltip.

### Global Components

- Page header with title, description, and optional compact statistic.
- Alerts and validation messages.
- Loading and empty states.
- Primary, secondary, icon, destructive, and toggle buttons.
- Text inputs, textareas, selects, date inputs, and numeric inputs.
- Priority and status pills.
- Count badges.
- Progress bars.
- Initial-based avatars.
- Panels and repeated-item cards.
- Desktop sidebar.
- Tablet navigation rail.
- Mobile application bar.
- Mobile bottom navigation.

## Page 1: Authentication

A contained authentication page supporting login and registration.

### Components

- Momentum heading.
- Email input.
- Password input.
- Login or Create Account primary button.
- Text button for switching authentication mode.
- Inline error alert.
- Disabled and loading button states.

### Desktop Layout

Use a dark branded band on the left and position the authentication panel
toward the center-right.

### Mobile Layout

Use a simple full-width canvas with a contained form panel.

## Page 2: Today

The default home screen and primary task command center.

### Header

- Page title: Today.
- Current formatted date.
- Daily plan completion percentage.

### Quick-Add Composer

The responsive task composer contains:

- Task title input.
- Priority selector.
- Category selector.
- Scheduled date input.
- Estimated minutes input.
- Focus toggle using a star icon.
- Privacy toggle using a lock for private and globe for public.
- Add button.

Desktop should use one row when space permits. Tablet should use two or three
intentional rows. Mobile should use a two-column form with the title and Add
button spanning the full width.

### Daily Summary

Display four metrics:

- Completed today.
- Remaining today.
- Planned effort.
- Current streak.

### Task Queues

Display three sections:

- Overdue.
- Today.
- Next 7 days.

Each task row contains:

- Circular Complete button.
- Task title.
- Focus star when applicable.
- Category.
- Estimated duration.
- Planned date.
- Priority pill.
- Start task action.
- Move to tomorrow action.

### Supporting Panels

- Latest achievement.
- Workspace summary containing active tasks, overall completion rate, and
  category count.

### Required States

- Empty queue.
- Overdue warning.
- Todo task.
- In-progress task.
- Focus task.
- Low, medium, and high priority.
- Completing or loading state.

## Page 3: Tasks

A complete task-management view.

### Header

- Page title: Tasks.
- Supporting description.
- Active task count.

### Task Composer

- Task title input.
- Description textarea.
- Priority selector.
- Category selector.
- Add task button.
- Inline category creation input.
- Icon-only category creation button.

### Task Library

Each task item contains:

- Status-colored vertical indicator.
- Title.
- Description.
- Priority pill.
- Todo, In Progress, or Done status pill.
- Complete action.
- Delete action.

### Responsive Layout

- Desktop: sticky task composer on the left and task library on the right.
- Tablet and mobile: composer above task library.
- Mobile: task actions move beneath the task text.

### Required States

- Empty task library.
- Completed task with reduced emphasis.
- Loading or disabled composer.
- Long title and description handling.

## Page 4: Social

A social accountability page centered on shared task completions.

### Profile Summary

- Avatar.
- Display name.
- Current goal or biography.
- Current level.
- Total XP.
- XP progress bar.
- Current streak.

### Badge Showcase

Display up to three unlocked badges as compact gold-accented items.

### Activity Feed

Each completion post contains:

- Author avatar.
- Display name.
- Author level.
- Relative timestamp.
- Completed task title.
- XP earned.
- Heart or encouragement reaction.
- Reaction count.
- Active reacted state.

The feed includes the current user's public completions and public completions
from followed users.

### Profile Editor

- Display name input.
- Current goal textarea.
- Save Profile button.

### People List

Each person row contains:

- Avatar.
- Display name.
- Level.
- Follow or unfollow icon button.

### Privacy Behavior

- Private task completions never appear in the feed.
- Public task completions generate a feed item.
- Each user can react once per post.

### Responsive Layout

- Desktop: activity feed with a profile and people panel on the right.
- Tablet: supporting sections arranged beside or below the feed.
- Mobile: all content stacked vertically.

## Page 5: Gamification / Progress

A progression hub derived from real productivity activity.

### Level Summary

Use a dark teal progression panel containing:

- Current level.
- Total XP.
- XP required for the next level.
- XP progress bar.
- Current day streak with a flame icon.

### Active Quests

The current quest types are:

- Complete two tasks today.
- Complete one focus task today.
- Complete five tasks this week.
- Complete two public tasks this week.

Each quest card contains:

- Daily or weekly cadence.
- Quest title.
- Description.
- XP reward.
- Progress bar.
- Numeric progress.
- Time remaining.
- Completed state with a checkmark.

### Badge Collection

The current badges are:

- First Win.
- Momentum.
- Deep Focus.
- Deadline Keeper.
- Open Book.
- Three-Day Rhythm.
- Century.

Each badge card contains:

- Badge icon or lock icon.
- Category.
- Rarity: Common, Rare, Epic, or Legendary.
- Title.
- Description.
- Progress bar.
- Numeric progress or unlock date.
- Locked or unlocked state.

### Visual Treatment

- Unlocked badges receive stronger gold or category accents.
- Locked badges use quieter gray surfaces.
- Rare, epic, and legendary states should be distinguishable without making
  the interface feel like a fantasy game.

## Page 6: Statistics

An analytics dashboard generated from task event history.

### Header

- Page title: Statistics.
- Supporting description.
- Overall completion-rate statistic.

### Filter Panel

- From date.
- To date.
- Interval selector with Daily, Weekly, and Monthly options.
- Apply button.

### Metric Tiles

Display six metrics:

- Created.
- Completed.
- Deleted.
- On time.
- Overdue.
- No deadline.

Use different top-border colors for positive, neutral, and problematic metrics.

### Activity Trend

Use grouped bars for:

- Created tasks.
- Completed tasks.
- Deleted tasks.

Include a legend, date labels, empty-data state, and horizontal scrolling
inside the chart only when the date range is large.

### Breakdown Charts

Use horizontal bar charts for:

- Tasks by status.
- Completed tasks by priority.
- Completed tasks by category.

### Responsive Behavior

- Desktop: six metrics in one row and three breakdown panels.
- Tablet: metrics and charts reduce to two or three columns.
- Mobile: two metric columns and vertically stacked charts.
- Filter controls become a single-column form on small mobile screens.

## Shared Component States

Create variants for:

- Loading.
- Empty.
- Error.
- Disabled.
- Hover.
- Keyboard focus.
- Selected.
- Completed.
- Locked.
- Unlocked.
- Overdue.
- Private.
- Public.
- Followed.
- Reacted.

## Reusable Component Library

Create reusable Figma components for:

- Desktop sidebar.
- Tablet navigation rail.
- Mobile app bar.
- Mobile bottom navigation.
- Page header.
- Metric tile.
- Panel.
- Task row.
- Priority pill.
- Status pill.
- Count badge.
- Icon button.
- Avatar.
- XP progress bar.
- Quest card.
- Badge card.
- Feed post.
- Person row.
- Form field.
- Toggle control.
- Date control.
- Duration control.
- Empty state.
- Alert.
- Bar chart.
- Chart legend.

## Design Tokens

Define reusable variables for:

- Brand, surface, canvas, text, muted, border, success, warning, danger, gold,
  and informational colors.
- Typography families, sizes, weights, and line heights.
- Spacing scale.
- Border widths.
- Corner radii.
- Subtle elevation and shadow levels.
- Responsive container widths and navigation sizes.

## Requested Figma Deliverables

1. Design-token collection.
2. Responsive component library with variants.
3. All six application pages.
4. Desktop, compact laptop, tablet, and mobile frames.
5. Interactive navigation prototype.
6. Form validation and component-state examples.
7. Responsive behavior annotations for quick-add, task rows, feeds, quests,
   badges, and analytics charts.

